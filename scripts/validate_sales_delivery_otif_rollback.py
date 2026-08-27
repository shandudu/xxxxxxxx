"""Validate shipment, delivery confirmation and OTIF snapshot persistence."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.sales.enums import DeliveryPerformanceStatus
from backend.plugin.sales.model import SalesOrder, Shipment
from backend.plugin.sales.service import delivery_service, sales_service


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                order = await db.scalar(
                    select(SalesOrder)
                    .where(SalesOrder.sales_order_no == 'DEMO-SOD-SO-001', SalesOrder.deleted == 0)
                )
                if not order:
                    raise RuntimeError('sales order missing')
                shipment = await db.scalar(
                    select(Shipment)
                    .where(Shipment.shipment_no == 'DEMO-SOD-SHP-001', Shipment.deleted == 0)
                )
                if not shipment:
                    raise RuntimeError('shipment missing')
                before = await delivery_service.list_order_performance(db, order.id)
                if not before or before[0].otif_status != DeliveryPerformanceStatus.IN_TRANSIT:
                    raise RuntimeError(f'expected IN_TRANSIT, got {before[0].otif_status if before else None}')
                await sales_service.deliver_shipment(db, shipment.id)
                after = await delivery_service.list_order_performance(db, order.id)
                if not after or after[0].otif_status != DeliveryPerformanceStatus.OTIF:
                    raise RuntimeError(f'expected OTIF, got {after[0].otif_status if after else None}')
                dashboard = await delivery_service.dashboard(db)
                print(
                    f'SALES_DELIVERY_OTIF_RUN_OK order={order.sales_order_no} '
                    f'status={after[0].otif_status} otif_rate={dashboard.otif_rate}'
                )
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('SALES_DELIVERY_OTIF_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
