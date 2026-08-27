"""Validate mobile fixed-asset lookup, idempotent scanning and live location variance."""
from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import CostCenterCreate, FinancePeriodCreate, FixedAssetCountApprovalRequest, FixedAssetCountCreate, FixedAssetCountScanRequest, FixedAssetCreate
from backend.plugin.finance.service import finance_service


class _Rollback(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2100-03-MOBILE', start_date=date(2100, 3, 1), end_date=date(2100, 3, 31)))
                book = await finance_service.create_cost_center(db, CostCenterCreate(center_code='CC-MOBILE-BOOK', center_name='账面成本中心'))
                actual = await finance_service.create_cost_center(db, CostCenterCreate(center_code='CC-MOBILE-ACTUAL', center_name='实盘成本中心'))
                asset = await finance_service.create_fixed_asset(db, FixedAssetCreate(period_id=period.id, asset_name='移动盘点设备', category='设备', acquisition_date=date(2100, 3, 1), original_value=Decimal('1200'), useful_life_months=60, barcode='BC-MOBILE-001', serial_number='SN-MOBILE-001', cost_center_id=book.id))
                count = await finance_service.create_fixed_asset_count(db, FixedAssetCountCreate(period_id=period.id, lines=[{'asset_id': asset.id}]))
                looked = await finance_service.lookup_fixed_asset(db, 'BC-MOBILE-001')
                first = await finance_service.scan_fixed_asset_count(db, count.id, FixedAssetCountScanRequest(code='SN-MOBILE-001', observed_cost_center_id=actual.id))
                second = await finance_service.scan_fixed_asset_count(db, count.id, FixedAssetCountScanRequest(code='SN-MOBILE-001', observed_cost_center_id=actual.id, remark='重复扫码应幂等'))
                approval = await finance_service.approve_fixed_asset_count_line(db, count.id, first.line.id, FixedAssetCountApprovalRequest(status='APPROVED', evidence_photo='validator://evidence'))
                posted = await finance_service.post_fixed_asset_count(db, count.id)
                if looked.id != asset.id or first.line.variance_type != 'LOCATION_MISMATCH' or second.is_new or approval.approval_status != 'APPROVED' or posted.status != 'POSTED' or len((await finance_service.fixed_asset_count_detail(db, count.id)).lines) != 1:
                    raise RuntimeError('mobile fixed asset count validation failed')
                print(f'FIXED_ASSET_MOBILE_COUNT_OK task={count.task_no} asset={asset.asset_no} variance={first.line.variance_type} idempotent={not second.is_new}')
                if not commit:
                    raise _Rollback
        except _Rollback:
            print('FIXED_ASSET_MOBILE_COUNT_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
