"""Exercise the NCR/MRB/rework/retest path in MySQL and roll it back by default."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import REFERENCES, SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.quality.enums import DispositionType, InspectionResult, ReworkStatus
from backend.plugin.quality.model import QualityInspection, QualityReworkOrder
from backend.plugin.quality.schema.quality import CompleteInspection, CreateDisposition, CreateInspection, CreateNcr
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.production.schema.production import CreateProductionReport
from backend.plugin.production.service.production_service import production_service
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
                await production_service.report_completion(
                    db,
                    CreateProductionReport(
                        report_no='QA-ROLLBACK-REWORK-RPT-001',
                        work_order_id=rework.production_work_order_id,
                        good_quantity=Decimal('2'),
                        warehouse_id=warehouse.id,
                        location_id=location.id,
                        lot_id=rework.lot_id,
                        remark='rollback rework production report',
                    ),
                )
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
