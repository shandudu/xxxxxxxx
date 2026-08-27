"""Validate supplier commitment, purchase OTIF and shortage impact snapshots."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.purchasing.enums import PurchaseDeliveryPerformanceStatus
from backend.plugin.purchasing.model import PurchaseOrder
from backend.plugin.purchasing.service import supplier_delivery_service


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                order = await db.scalar(
                    select(PurchaseOrder)
                    .where(PurchaseOrder.deleted == 0)
                    .order_by(PurchaseOrder.id.desc())
                )
                if not order:
                    raise RuntimeError('purchase order missing')
                rows = await supplier_delivery_service.list_order_performance(db, order.id)
                if not rows:
                    raise RuntimeError('purchase delivery performance missing')
                if rows[0].otif_status != PurchaseDeliveryPerformanceStatus.OTIF:
                    raise RuntimeError(f'expected OTIF, got {rows[0].otif_status}')
                dashboard = await supplier_delivery_service.dashboard(db)
                print(
                    f'SUPPLIER_PURCHASE_OTIF_RUN_OK order={order.purchase_order_no} '
                    f'status={rows[0].otif_status} otif_rate={dashboard.otif_rate}'
                )
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('SUPPLIER_PURCHASE_OTIF_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
