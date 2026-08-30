"""Exercise the NCR/MRB/rework/retest path in MySQL and roll it back by default."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import func, select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import REFERENCES, SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.quality.enums import DispositionType, InspectionResult, ReworkStatus
from backend.plugin.quality.model import QualityInspection, QualityReworkOrder
from backend.plugin.quality.schema.quality import CompleteInspection, CreateDisposition, CreateInspection, CreateNcr
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.production.model import ProductionReport
from backend.plugin.production.schema.production import CreateProductionReport
from backend.plugin.production.service.production_service import production_service
from backend.plugin.trace.enums import LotSourceType, LotType, QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.plugin.warehouse.model import Location, Warehouse


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                lot = await db.scalar(
                    select(MaterialLot).where(
                        MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'],
                        MaterialLot.deleted == 0,
                    )
                )
                if not lot:
                    raise RuntimeError('finished lot missing')
                concession_lot = MaterialLot(
                    lot_no='QA-ROLLBACK-CONCESSION-LOT',
                    material_id=lot.material_id,
                    lot_type=LotType.FINISHED,
                    source_type=LotSourceType.MANUAL,
                    quantity=Decimal('2'),
                    unit_id=lot.unit_id,
                    quality_status=QualityStatus.HOLD,
                )
                db.add(concession_lot)
                await db.flush()
                concession_inspection = await quality_service.create_inspection(
                    db,
                    CreateInspection(
                        inspection_no='QA-ROLLBACK-CONCESSION-QI',
                        inspection_type='FINAL',
                        material_id=concession_lot.material_id,
                        lot_id=concession_lot.id,
                        source_type='QUALITY_ROLLBACK_TEST',
                        source_no='QA-CONCESSION',
                        sample_quantity=Decimal('2'),
                    ),
                )
                await quality_service.complete_inspection(
                    db,
                    concession_inspection.id,
                    CompleteInspection(
                        accepted_quantity=Decimal('0'),
                        rejected_quantity=Decimal('2'),
                        result=InspectionResult.FAIL,
                        conclusion='partial concession validation',
                    ),
                )
                concession_ncr = await quality_service.create_ncr(
                    db,
                    CreateNcr(
                        ncr_no='QA-ROLLBACK-CONCESSION-NCR',
                        inspection_id=concession_inspection.id,
                        nonconforming_quantity=Decimal('2'),
                        defect_description='partial concession validation',
                    ),
                )
                for index in (1, 2):
                    concession = await quality_service.create_disposition(
                        db,
                        CreateDisposition(
                            disposition_no=f'QA-ROLLBACK-CONCESSION-MRB-{index}',
                            ncr_id=concession_ncr.id,
                            disposition_type=DispositionType.USE_AS_IS,
                            quantity=Decimal('1'),
                            decision_reason='concession validation',
                        ),
                    )
                    await quality_service.execute_disposition(db, concession.id)
                    await db.refresh(concession_lot)
                    expected_status = QualityStatus.HOLD if index == 1 else QualityStatus.PASS
                    if concession_lot.quality_status != expected_status:
                        raise RuntimeError(
                            f'concession lot status invalid after part {index}: '
                            f'{concession_lot.quality_status}'
                        )
                inspection = await quality_service.create_inspection(
                    db,
                    CreateInspection(
                        inspection_no='QA-ROLLBACK-FAIL-001',
                        inspection_type='FINAL',
                        material_id=lot.material_id,
                        lot_id=lot.id,
                        source_type='QUALITY_ROLLBACK_TEST',
                        source_no='QA-ROLLBACK',
                        sample_quantity=Decimal('2'),
                    ),
                )
                await quality_service.complete_inspection(
                    db,
                    inspection.id,
                    CompleteInspection(
                        accepted_quantity=Decimal('0'),
                        rejected_quantity=Decimal('2'),
                        result=InspectionResult.FAIL,
                        conclusion='rollback test',
                    ),
                )
                ncr = await quality_service.create_ncr(
                    db,
                    CreateNcr(
                        ncr_no='QA-ROLLBACK-NCR-001',
                        inspection_id=inspection.id,
                        nonconforming_quantity=Decimal('2'),
                        defect_description='rollback test defect',
                    ),
                )
                try:
                    await quality_service.create_ncr(
                        db,
                        CreateNcr(
                            ncr_no='QA-ROLLBACK-NCR-OVERFLOW',
                            inspection_id=inspection.id,
                            nonconforming_quantity=Decimal('1'),
                            defect_description='must exceed cumulative rejected quantity',
                        ),
                    )
                except errors.ConflictError as exc:
                    if exc.msg != 'NCR_QUANTITY_EXCEEDS_REJECTED':
                        raise
                else:
                    raise RuntimeError('cumulative NCR quantity overflow was accepted')
                disposition = await quality_service.create_disposition(
                    db,
                    CreateDisposition(
                        disposition_no='QA-ROLLBACK-MRB-001',
                        ncr_id=ncr.id,
                        disposition_type=DispositionType.REWORK,
                        quantity=Decimal('2'),
                    ),
                )
                await quality_service.execute_disposition(db, disposition.id)
                rework = await db.scalar(
                    select(QualityReworkOrder).where(QualityReworkOrder.ncr_id == ncr.id)
                )
                if not rework:
                    raise RuntimeError('rework task missing')
                await quality_service.create_rework_work_order(db, rework.id)
                await quality_service.start_rework(db, rework.id)
                rework = await db.scalar(select(QualityReworkOrder).where(QualityReworkOrder.id == rework.id))
                warehouse = await db.scalar(select(Warehouse).where(Warehouse.warehouse_code == REFERENCES['warehouse'], Warehouse.deleted == 0))
                location = await db.scalar(select(Location).where(Location.location_code == REFERENCES['location'], Location.deleted == 0))
                if not rework or not warehouse or not location:
                    raise RuntimeError('rework production references missing')
                report_request = CreateProductionReport(
                    report_no='QA-ROLLBACK-REWORK-RPT-001',
                    idempotency_key='qa-rollback-rework-report-001',
                    work_order_id=rework.production_work_order_id,
                    good_quantity=Decimal('2'),
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    lot_id=rework.lot_id,
                    remark='rollback rework production report',
                )
                first_report = await production_service.report_completion(db, report_request)
                retry_report = await production_service.report_completion(db, report_request)
                if retry_report.id != first_report.id:
                    raise RuntimeError('production report retry created a duplicate')
                try:
                    await production_service.report_completion(
                        db,
                        report_request.model_copy(update={'good_quantity': Decimal('1')}),
                    )
                except errors.ConflictError as exc:
                    if exc.msg != 'PRODUCTION_REPORT_IDEMPOTENCY_CONFLICT':
                        raise
                else:
                    raise RuntimeError('production report idempotency conflict was accepted')
                report_count = await db.scalar(select(func.count(ProductionReport.id)).where(
                    ProductionReport.idempotency_key == report_request.idempotency_key,
                    ProductionReport.deleted == 0,
                ))
                if report_count != 1:
                    raise RuntimeError(f'production report retry count invalid: {report_count}')
                await quality_service.complete_rework(db, rework.id)
                rework = await db.scalar(select(QualityReworkOrder).where(QualityReworkOrder.id == rework.id))
                retest = await db.scalar(select(QualityInspection).where(QualityInspection.id == rework.reinspection_id))
                await quality_service.complete_inspection(
                    db,
                    retest.id,
                    CompleteInspection(
                        accepted_quantity=Decimal('2'),
                        rejected_quantity=Decimal('0'),
                        result=InspectionResult.PASS,
                        conclusion='rollback retest passed',
                    ),
                )
                await quality_service.close_ncr(db, ncr.id, 'rollback test root cause')
                if rework.status != ReworkStatus.RELEASED:
                    raise RuntimeError('rework was not released')
                print('QUALITY_NCR_REWORK_RUN_OK status=RELEASED')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('QUALITY_NCR_REWORK_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain test/demo data instead of rolling back')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
