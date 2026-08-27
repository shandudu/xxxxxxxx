"""Validate ATP/CTP sales-order promise assessment and risk persistence."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.sales.model import SalesOrder, SalesOrderPromiseAssessment
from backend.plugin.sales.service import promise_service


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                order = await db.scalar(select(SalesOrder).where(SalesOrder.deleted == 0).order_by(SalesOrder.id.desc()))
                if not order:
                    raise RuntimeError('sales order missing')
                assessments = await promise_service.assess_order(db, order.id)
                if not assessments:
                    raise RuntimeError('promise assessment missing')
                dashboard = await promise_service.dashboard(db)
                persisted = list((await db.scalars(select(SalesOrderPromiseAssessment).where(SalesOrderPromiseAssessment.sales_order_id == order.id, SalesOrderPromiseAssessment.deleted == 0))).all())
                if len(persisted) != len(assessments):
                    raise RuntimeError('promise persistence mismatch')
                print(f'SALES_PROMISE_RUN_OK order={order.sales_order_no} risk={assessments[0].risk_status} delayed={dashboard.delayed_order_count}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('SALES_PROMISE_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
