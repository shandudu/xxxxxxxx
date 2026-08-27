"""Validate the complete manufacturing happy path in a real DB transaction.

The default mode rolls the transaction back, so it can be used against a
development or staging MySQL database without leaving demo business data.
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
                result = await demo_service.run(db)
                verification = await demo_service.verify(db)
                print(
                    f'MANUFACTURING_HAPPY_PATH_RUN_OK status={result.status} '
                    f'passed={verification.passed} missing={len(verification.missing_steps)}'
                )
                if not verification.passed:
                    raise RuntimeError(f'演示闭环校验失败: {verification.missing_steps}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('MANUFACTURING_HAPPY_PATH_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain demo data instead of rolling back')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
