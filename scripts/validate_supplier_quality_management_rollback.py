"""Validate IQC -> NCR -> SCAR -> retest -> score -> purchasing linkage in MySQL."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.purchasing.schema.purchasing import (
    ConfirmPurchaseOrder,
    CreatePurchaseOrder,
    CreatePurchaseOrderLine,
    CreateSupplierReceipt,
    CreateSupplierReceiptLine,
)
from backend.plugin.purchasing.service import purchasing_service
from backend.plugin.quality.enums import (
    InspectionResult,
    InspectionStatus,
    InspectionType,
    NcrStatus,
    SupplierCorrectiveActionStatus,
    SupplierProcurementDecision,
)
from backend.plugin.quality.model import NonconformanceReport, QualityInspection, SupplierCorrectiveAction
from backend.plugin.quality.schema.quality import CompleteInspection, CreateInspection, CreateNcr
from backend.plugin.quality.schema.sqm import (
    IssueSupplierCorrectiveAction,
    RespondSupplierCorrectiveAction,
    SupplierQualityPolicyUpsert,
    VerifySupplierCorrectiveAction,
)
from backend.plugin.quality.service import quality_service, sqm_service
from backend.plugin.supplier.enums import SupplierQualityStatus
from backend.plugin.trace.enums import QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.utils.timezone import timezone


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                data = await demo_service._ensure_master_data(db)
                supplier = data['supplier']
                material = data['raw']
                warehouse = data['warehouse']
                location = data['location']
                now = timezone.now()
                run_key = uuid4().hex[:8].upper()
                supplier.quality_status = SupplierQualityStatus.QUALIFIED
                supplier.purchasing_enabled = True
                await sqm_service.upsert_policy(
                    db,
                    supplier.id,
                    SupplierQualityPolicyUpsert(
                        rolling_days=180,
                        minimum_inspections=1,
                        excellent_score=90,
                        qualified_score=70,
                        conditional_score=40,
                        quality_weight=70,
                        delivery_weight=30,
                        auto_apply=True,
                        block_on_open_critical_scar=True,
                    ),
                )

                order = await purchasing_service.create_order(
                    db,
                    CreatePurchaseOrder(
                        purchase_order_no=f'SQM-PO-{run_key}',
                        supplier_id=supplier.id,
                        lines=[CreatePurchaseOrderLine(
                            material_id=material.id,
                            ordered_quantity=Decimal('5'),
                            requested_delivery_at=now + timedelta(days=1),
                        )],
                    ),
                )
                await purchasing_service.confirm_order(
                    db,
                    order.id,
                    ConfirmPurchaseOrder(supplier_confirmed_delivery_at=now + timedelta(days=1)),
                )
                receipt = await purchasing_service.create_receipt(
                    db,
                    CreateSupplierReceipt(
                        receipt_no=f'SQM-RCV-{run_key}',
                        purchase_order_id=order.id,
                        lines=[CreateSupplierReceiptLine(
                            purchase_order_line_id=order.lines[0].id,
                            warehouse_id=warehouse.id,
                            location_id=location.id,
                            quantity=Decimal('5'),
                            lot_no=f'SQM-LOT-{run_key}',
                            supplier_lot_no=f'SUP-{run_key}',
                        )],
                    ),
                )
                lot = await db.scalar(select(MaterialLot).where(
                    MaterialLot.lot_no == f'SQM-LOT-{run_key}', MaterialLot.deleted == 0
                ))
                inspection = await db.scalar(select(QualityInspection).where(
                    QualityInspection.source_type == 'SUPPLIER_RECEIPT',
                    QualityInspection.source_id == receipt.id,
                    QualityInspection.lot_id == lot.id,
                    QualityInspection.deleted == 0,
                ))
                if inspection is None:
                    inspection = await quality_service.create_inspection(
                        db,
                        CreateInspection(
                            inspection_no=f'SQM-IQC-{run_key}',
                            inspection_type=InspectionType.INCOMING,
                            material_id=material.id,
                            lot_id=lot.id,
                            source_type='SUPPLIER_RECEIPT',
                            source_id=receipt.id,
                            source_no=receipt.receipt_no,
                            sample_quantity=Decimal('5'),
                        ),
                    )
                await quality_service.complete_inspection(
                    db,
                    inspection.id,
                    CompleteInspection(
                        accepted_quantity=Decimal('0'),
                        rejected_quantity=Decimal('5'),
                        result=InspectionResult.FAIL,
                        conclusion='来料尺寸严重超差',
                    ),
                )
                ncr = await quality_service.create_ncr(
                    db,
                    CreateNcr(
                        ncr_no=f'SQM-NCR-{run_key}',
                        inspection_id=inspection.id,
                        nonconforming_quantity=Decimal('5'),
                        defect_description='来料尺寸严重超差',
                        severity='CRITICAL',
                    ),
                )
                scar = await db.scalar(select(SupplierCorrectiveAction).where(
                    SupplierCorrectiveAction.ncr_id == ncr.id,
                    SupplierCorrectiveAction.deleted == 0,
                ))
                if not scar or scar.status != SupplierCorrectiveActionStatus.DRAFT:
                    raise RuntimeError('incoming NCR did not create one draft SCAR')
                await sqm_service.issue_scar(
                    db,
                    scar.id,
                    IssueSupplierCorrectiveAction(due_at=now + timedelta(days=7)),
                )
                try:
                    await purchasing_service.create_order(
                        db,
                        CreatePurchaseOrder(
                            purchase_order_no=f'SQM-BLOCK-{run_key}',
                            supplier_id=supplier.id,
                            lines=[CreatePurchaseOrderLine(
                                material_id=material.id, ordered_quantity=Decimal('1')
                            )],
                        ),
                    )
                except errors.ConflictError as exc:
                    if exc.msg not in {'SUPPLIER_CRITICAL_SCAR_OPEN', 'SUPPLIER_SQM_SUSPENDED'}:
                        raise
                else:
                    raise RuntimeError('purchase order was allowed with critical open SCAR')

                await sqm_service.respond_scar(
                    db,
                    scar.id,
                    RespondSupplierCorrectiveAction(
                        containment_action='隔离在途与库存批次',
                        root_cause='量具校准漂移导致加工尺寸超差',
                        corrective_action='校准量具并重做首件确认',
                        preventive_action='增加班前量具点检和过程审核',
                        response_evidence='校准证书与首件报告已上传',
                    ),
                )
                await sqm_service.create_reinspection(db, scar.id)
                await db.refresh(scar)
                retest = await db.scalar(select(QualityInspection).where(
                    QualityInspection.id == scar.reinspection_id,
                    QualityInspection.deleted == 0,
                ))
                await quality_service.complete_inspection(
                    db,
                    retest.id,
                    CompleteInspection(
                        accepted_quantity=Decimal('5'),
                        rejected_quantity=Decimal('0'),
                        result=InspectionResult.PASS,
                        conclusion='整改批次复验通过',
                    ),
                )
                closed_scar = await sqm_service.verify_scar(
                    db,
                    scar.id,
                    VerifySupplierCorrectiveAction(verification_notes='量具与批次复验均符合要求'),
                )
                assessment = (await sqm_service.list_assessments(db, supplier.id, 1))[0]
                await db.refresh(lot)
                final_ncr = await db.scalar(select(NonconformanceReport).where(
                    NonconformanceReport.id == ncr.id
                ))
                if closed_scar.status != SupplierCorrectiveActionStatus.CLOSED:
                    raise RuntimeError('SCAR was not closed after passed reinspection')
                if retest.status != InspectionStatus.COMPLETED or lot.quality_status != QualityStatus.PASS:
                    raise RuntimeError('reinspection did not release lot quality state')
                if final_ncr.status != NcrStatus.DISPOSED:
                    raise RuntimeError(f'NCR did not follow the SCAR reinspection: {final_ncr.status}')
                if assessment.procurement_decision != SupplierProcurementDecision.CONDITIONAL:
                    raise RuntimeError(f'unexpected supplier decision: {assessment.procurement_decision}')

                recovery_order = await purchasing_service.create_order(
                    db,
                    CreatePurchaseOrder(
                        purchase_order_no=f'SQM-RECOVER-{run_key}',
                        supplier_id=supplier.id,
                        lines=[CreatePurchaseOrderLine(
                            material_id=material.id, ordered_quantity=Decimal('1')
                        )],
                    ),
                )
                if not recovery_order.id:
                    raise RuntimeError('conditional supplier purchasing did not recover')
                print(
                    'SUPPLIER_QUALITY_MANAGEMENT_RUN_OK '
                    f'scar={closed_scar.status} ncr={final_ncr.status} '
                    f'grade={assessment.grade} decision={assessment.procurement_decision} '
                    'critical_blocked=True recovered=True'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('SUPPLIER_QUALITY_MANAGEMENT_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
