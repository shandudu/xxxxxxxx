"""Validate production costing and margin analysis in a rollback-safe transaction."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal

from backend.database.db import async_db_session
from backend.plugin.costing.enums import MarginDimension
from backend.plugin.costing.schema.costing import CostPeriodCreate
from backend.plugin.costing.service import costing_service
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.production.model import WorkOrder
from sqlalchemy import select


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run(db)
                period = await costing_service.create_period(db, CostPeriodCreate(period_code='2099-12', start_date=date(2099, 12, 1), end_date=date(2099, 12, 31), labor_rate_per_hour=Decimal('80'), machine_rate_per_hour=Decimal('40'), overhead_rate_per_hour=Decimal('20')))
                work_order = await db.scalar(select(WorkOrder).where(WorkOrder.work_order_no == 'DEMO-WO-001', WorkOrder.deleted == 0))
                if work_order is None:
                    raise RuntimeError('demo work order missing')
                trial = await costing_service.calculate_work_order(db, work_order.id, period.id)
                posted = await costing_service.post_work_order(db, work_order.id, period.id)
                margin = await costing_service.margin(db, period.id, MarginDimension.PRODUCT)
                if str(getattr(posted.status, 'value', posted.status)) != 'POSTED' or trial.total_cost < 0 or margin.revenue < 0:
                    raise RuntimeError('costing verification failed')
                print(f'COSTING_RUN_OK work_order={work_order.work_order_no} total={posted.total_cost} margin_rows={len(margin.rows)}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('COSTING_MARGIN_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
