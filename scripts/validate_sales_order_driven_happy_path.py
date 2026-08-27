"""Validate the sales-order-driven happy path in a real DB transaction.

By default the transaction is intentionally rolled back, so this is safe for a
development database. Pass ``--commit`` only when demo data should be retained.
"""

from __future__ import annotations

import argparse
import asyncio

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                result = await demo_service.run_sales_order_driven(db)
                print(f'SALES_ORDER_DRIVEN_RUN_OK status={result.status}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('SALES_ORDER_DRIVEN_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain demo data instead of rolling back')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
