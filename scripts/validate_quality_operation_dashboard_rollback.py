"""Validate the quality/after-sales operations dashboard and SLA alert loop."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.demo.service.demo_service import SALES_ORDER_DRIVEN_REFERENCES
from backend.plugin.quality.enums import InspectionResult
from backend.plugin.quality.schema.quality import CompleteInspection, CreateInspection, CreateNcr
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.quality.model import QualityWorkItemAlertEvent
from backend.plugin.trace.model import MaterialLot


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                lot = await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'], MaterialLot.deleted == 0))
                if lot:
                    inspection = await quality_service.create_inspection(db, CreateInspection(inspection_no='OPS-DASH-INS-001', inspection_type='FINAL', material_id=lot.material_id, lot_id=lot.id, sample_quantity=Decimal('1')))
                    await quality_service.complete_inspection(db, inspection.id, CompleteInspection(accepted_quantity=Decimal('0'), rejected_quantity=Decimal('1'), result=InspectionResult.FAIL, conclusion='dashboard validation'))
                    await quality_service.create_ncr(db, CreateNcr(ncr_no='OPS-DASH-NCR-001', inspection_id=inspection.id, nonconforming_quantity=Decimal('1'), defect_description='dashboard validation defect'))
                summary = await quality_service.operation_dashboard(db)
                if not summary.status_counts or 'NCR' not in summary.status_counts:
                    raise RuntimeError('dashboard status counts missing')
                alerts = list(await quality_service.list_sla_alerts(db))
                if not alerts:
                    raise RuntimeError('dashboard did not materialize SLA alert')
                if alerts:
                    alert = alerts[0]
                    await quality_service.acknowledge_sla_alert(db, alert.id)
                    await quality_service.escalate_sla_alert(db, alert.id, 1)
                    await quality_service.close_sla_alert(db, alert.id)
                    events = list((await db.scalars(select(QualityWorkItemAlertEvent).where(QualityWorkItemAlertEvent.alert_id == alert.id))).all())
                    if len(events) != 3:
                        raise RuntimeError('SLA alert event history incomplete')
                print(f'QUALITY_OPERATION_DASHBOARD_RUN_OK overdue={sum(summary.overdue_counts.values())} alerts={len(alerts)}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('QUALITY_OPERATION_DASHBOARD_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
