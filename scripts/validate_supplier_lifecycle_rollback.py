"""Validate supplier qualification -> sample -> PPAP -> AVL -> review with rollback."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.purchasing.schema.purchasing import CreatePurchaseOrder, CreatePurchaseOrderLine
from backend.plugin.purchasing.service import purchasing_service
from backend.plugin.supplier.enums import (
    CompanyType, SupplierAuditResult, SupplierAuditType, SupplierAvlStatus,
    SupplierPpapStatus, SupplierQualificationStatus, SupplierReviewDecision, SupplierType,
)
from backend.plugin.supplier.model import (
    Supplier,
    SupplierApprovedMaterial,
    SupplierQualificationApplication,
)
from backend.plugin.supplier.schema.lifecycle import (
    CompletePeriodicReview, CompleteQualificationAudit, CreatePeriodicReview,
    CreatePpapSubmission, CreateQualificationApplication, CreateQualificationAudit,
    CreateSampleApproval, DecidePpapSubmission, DecideSampleApproval, QualificationDecision,
)
from backend.plugin.supplier.service import supplier_lifecycle_service
from backend.utils.timezone import timezone


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                data = await demo_service._ensure_master_data(db)
                source_supplier, material, other_material = data['supplier'], data['raw'], data['finished']
                run_key = uuid4().hex[:8].upper()
                supplier = Supplier(
                    supplier_code=f'AVL-{run_key}', supplier_name=f'AVL validation supplier {run_key}',
                    category_id=source_supplier.category_id, supplier_type=SupplierType.MATERIAL,
                    company_type=CompanyType.COMPANY,
                )
                db.add(supplier)
                await db.flush()

                application = await supplier_lifecycle_service.create_application(
                    db, CreateQualificationApplication(
                        supplier_id=supplier.id, requested_scope=f'{material.material_code} raw material supply',
                        certificate_manifest={'business_license': f'LIC-{run_key}', 'iso9001': f'ISO-{run_key}'},
                    ),
                )
                try:
                    await purchasing_service.create_order(
                        db, CreatePurchaseOrder(
                            purchase_order_no=f'AVL-BEFORE-{run_key}', supplier_id=supplier.id,
                            lines=[CreatePurchaseOrderLine(material_id=material.id, ordered_quantity=Decimal('1'))],
                        ),
                    )
                except errors.ConflictError:
                    blocked_before_approval = True
                else:
                    raise RuntimeError('supplier purchasing was allowed before qualification')

                await supplier_lifecycle_service.submit_application(db, application.id)
                audit = await supplier_lifecycle_service.create_audit(
                    db, application.id,
                    CreateQualificationAudit(audit_type=SupplierAuditType.INITIAL, planned_at=timezone.now()),
                )
                await supplier_lifecycle_service.complete_audit(
                    db, audit.id, CompleteQualificationAudit(
                        score=Decimal('92'), result=SupplierAuditResult.PASS,
                        findings='Quality system and manufacturing controls meet requirements',
                        evidence_manifest={'audit_report': f'AUD-{run_key}'},
                    ),
                )
                sample = await supplier_lifecycle_service.create_sample(
                    db, application.id, CreateSampleApproval(
                        material_id=material.id, submitted_quantity=Decimal('10'),
                        evidence_manifest={'sample_report': f'SAM-{run_key}'},
                    ),
                )
                await supplier_lifecycle_service.decide_sample(
                    db, sample.id, DecideSampleApproval(
                        approved=True, decision_notes='Sample dimensions and performance passed'
                    ),
                )
                ppap = await supplier_lifecycle_service.create_ppap(
                    db, application.id, CreatePpapSubmission(
                        material_id=material.id, level=3, version=f'1.0-{run_key}',
                        sample_approval_id=sample.id,
                        document_manifest={
                            'psw': f'PSW-{run_key}', 'control_plan': f'CP-{run_key}',
                            'pfmea': f'PFMEA-{run_key}', 'msa': f'MSA-{run_key}',
                        },
                    ),
                )
                await supplier_lifecycle_service.submit_ppap(db, ppap.id)
                approved_ppap = await supplier_lifecycle_service.decide_ppap(
                    db, ppap.id, DecidePpapSubmission(
                        approved=True, decision_notes='PPAP level 3 evidence approved', valid_days=365,
                    ),
                )
                approved_application = await supplier_lifecycle_service.approve_application(
                    db, application.id, QualificationDecision(
                        decision_notes='Supplier audit, sample, and PPAP passed', valid_days=365,
                        qualification_level='STANDARD',
                    ),
                )
                avl = await db.scalar(select(SupplierApprovedMaterial).where(
                    SupplierApprovedMaterial.supplier_id == supplier.id,
                    SupplierApprovedMaterial.material_id == material.id,
                    SupplierApprovedMaterial.deleted == 0,
                ))
                if not avl or avl.status != SupplierAvlStatus.APPROVED:
                    raise RuntimeError('qualification approval did not create approved AVL entry')
                order = await purchasing_service.create_order(
                    db, CreatePurchaseOrder(
                        purchase_order_no=f'AVL-AFTER-{run_key}', supplier_id=supplier.id,
                        lines=[CreatePurchaseOrderLine(material_id=material.id, ordered_quantity=Decimal('1'))],
                    ),
                )
                if not order.id:
                    raise RuntimeError('AVL-approved purchase order was not created')
                try:
                    await supplier_lifecycle_service.ensure_supplier_material_approved(
                        db, supplier.id, other_material.id
                    )
                except errors.ConflictError as exc:
                    if exc.msg != 'SUPPLIER_MATERIAL_NOT_IN_AVL':
                        raise
                    non_avl_blocked = True
                else:
                    raise RuntimeError('non-AVL material was allowed')

                review = await supplier_lifecycle_service.create_review(
                    db, avl.id, CreatePeriodicReview(planned_at=timezone.now())
                )
                completed_review = await supplier_lifecycle_service.complete_review(
                    db, review.id, CompletePeriodicReview(
                        decision=SupplierReviewDecision.SUSPEND,
                        notes='Periodic review found unacceptable risk', next_review_days=365,
                    ),
                )
                try:
                    await purchasing_service.create_order(
                        db, CreatePurchaseOrder(
                            purchase_order_no=f'AVL-SUSPEND-{run_key}', supplier_id=supplier.id,
                            lines=[CreatePurchaseOrderLine(material_id=material.id, ordered_quantity=Decimal('1'))],
                        ),
                    )
                except errors.ConflictError:
                    suspended_blocked = True
                else:
                    raise RuntimeError('suspended AVL supplier was allowed to purchase')

                await db.refresh(avl)
                final_application = await db.scalar(select(SupplierQualificationApplication).where(
                    SupplierQualificationApplication.id == approved_application.id,
                    SupplierQualificationApplication.deleted == 0,
                ))
                if final_application.status != SupplierQualificationStatus.SUSPENDED:
                    raise RuntimeError(f'application was not suspended: {final_application.status}')
                if approved_ppap.status != SupplierPpapStatus.APPROVED:
                    raise RuntimeError(f'PPAP status changed unexpectedly: {approved_ppap.status}')
                if avl.status != SupplierAvlStatus.SUSPENDED:
                    raise RuntimeError(f'AVL was not suspended: {avl.status}')
                print(
                    'SUPPLIER_LIFECYCLE_RUN_OK '
                    f'application={final_application.status} ppap={approved_ppap.status} avl={avl.status} '
                    f'review={completed_review.decision} blocked_before={blocked_before_approval} '
                    f'non_avl_blocked={non_avl_blocked} suspended_blocked={suspended_blocked}'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('SUPPLIER_LIFECYCLE_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
