"""Exercise the CAPA/8D workflow in MySQL and roll it back by default."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.quality.enums import CapaActionStatus, CapaActionType, CapaStatus, CapaVerificationResult, DispositionType, InspectionResult, InspectionType
from backend.plugin.quality.model import NonconformanceReport, QualityCapa, QualityInspection
from backend.plugin.quality.schema.quality import CompleteInspection, CreateCapa, CreateCapaAction, CreateDisposition, CreateInspection, CreateNcr, SetCapaActionStatus, VerifyCapa
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.trace.model import MaterialLot


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                lot = await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'], MaterialLot.deleted == 0))
                if not lot:
                    raise RuntimeError('finished lot missing')
                inspection = await quality_service.create_inspection(
                    db,
                    CreateInspection(inspection_no='CAPA-ROLLBACK-QI-001', inspection_type=InspectionType.FINAL, material_id=lot.material_id, lot_id=lot.id, source_type='CAPA_ROLLBACK', sample_quantity=Decimal('2')),
                )
                await quality_service.complete_inspection(db, inspection.id, CompleteInspection(accepted_quantity=Decimal('0'), rejected_quantity=Decimal('2'), result=InspectionResult.FAIL, conclusion='CAPA rollback test'))
                ncr = await quality_service.create_ncr(db, CreateNcr(inspection_id=inspection.id, nonconforming_quantity=Decimal('2'), defect_description='CAPA rollback defect'))
                disposition = await quality_service.create_disposition(db, CreateDisposition(disposition_no='CAPA-ROLLBACK-MRB-001', ncr_id=ncr.id, disposition_type=DispositionType.REINSPECT, quantity=Decimal('2'), decision_reason='CAPA rollback test'))
                await quality_service.execute_disposition(db, disposition.id)
                retest = await db.scalar(select(QualityInspection).where(QualityInspection.id == disposition.reinspection_id, QualityInspection.deleted == 0))
                if not retest:
                    raise RuntimeError('CAPA retest missing')
                await quality_service.complete_inspection(db, retest.id, CompleteInspection(accepted_quantity=Decimal('2'), rejected_quantity=Decimal('0'), result=InspectionResult.PASS, conclusion='CAPA retest passed'))
                ncr = await quality_service.get_ncr(db, ncr.id)
                capa = await quality_service.create_capa(db, CreateCapa(capa_no='CAPA-ROLLBACK-001', ncr_id=ncr.id, d2_problem_description='rollback defect', d4_root_cause='rollback root cause', d5_corrective_plan='rollback corrective plan'))
                action = await quality_service.create_capa_action(db, capa.id, CreateCapaAction(action_type=CapaActionType.CORRECTIVE, description='apply corrective action'))
                await quality_service.set_capa_action_status(db, capa.id, action.id, SetCapaActionStatus(status=CapaActionStatus.COMPLETED, evidence='action evidence'))
                await quality_service.verify_capa(db, capa.id, VerifyCapa(result=CapaVerificationResult.PASS, notes='effectiveness passed'))
                await quality_service.close_capa(db, capa.id)
                await quality_service.close_ncr(db, ncr.id, 'CAPA root cause')
                capa = await db.scalar(select(QualityCapa).where(QualityCapa.id == capa.id))
                ncr = await db.scalar(select(NonconformanceReport).where(NonconformanceReport.id == ncr.id))
                if not capa or capa.status != CapaStatus.CLOSED or not ncr or getattr(ncr.status, 'value', ncr.status) != 'CLOSED':
                    raise RuntimeError('CAPA/NCR did not close')
                print('QUALITY_CAPA_RUN_OK status=CLOSED')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('QUALITY_CAPA_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain test/demo data instead of rolling back')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
