"""Validate fixed asset count variance and book/tax depreciation ledgers."""
from __future__ import annotations
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import CostCenterCreate, FinancePeriodCreate, FixedAssetCountApprovalRequest, FixedAssetCountCreate, FixedAssetCountLineCreate, FixedAssetCreate
from backend.plugin.finance.service import finance_service

class _Rollback(Exception): pass

async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2100-02-ASSET', start_date=date(2100,2,1), end_date=date(2100,2,28)))
                center = await finance_service.create_cost_center(db, CostCenterCreate(center_code='CC-FACNT', center_name='固定资产盘点中心'))
                keep = await finance_service.create_fixed_asset(db, FixedAssetCreate(period_id=period.id, asset_name='在用设备', category='设备', acquisition_date=date(2100,2,1), original_value=Decimal('600'), useful_life_months=60, barcode='BC-KEEP', serial_number='SN-KEEP', cost_center_id=center.id))
                missing = await finance_service.create_fixed_asset(db, FixedAssetCreate(period_id=period.id, asset_name='盘点缺失设备', category='设备', acquisition_date=date(2100,2,1), original_value=Decimal('300'), useful_life_months=60, barcode='BC-MISS', serial_number='SN-MISS', cost_center_id=center.id))
                count = await finance_service.create_fixed_asset_count(db, FixedAssetCountCreate(period_id=period.id, lines=[FixedAssetCountLineCreate(asset_id=missing.id, counted=False)]))
                await finance_service.approve_fixed_asset_count_line(db, count.id, count.lines[0].id, FixedAssetCountApprovalRequest(status='APPROVED', evidence_photo='validator://evidence'))
                posted = await finance_service.post_fixed_asset_count(db, count.id)
                dual = await finance_service.run_fixed_asset_dual_depreciation(db, period.id)
                again = await finance_service.run_fixed_asset_dual_depreciation(db, period.id)
                missing_row = await finance_service._fixed_asset(db, missing.id)
                if missing_row.status != 'RETIRED' or not posted.lines or not dual.rows or again.total_tax_depreciation != dual.total_tax_depreciation:
                    raise RuntimeError('fixed asset count/dual depreciation validation failed')
                print(f'FIXED_ASSET_COUNT_DUAL_OK task={count.task_no} retired={missing_row.status} book={dual.total_book_depreciation} tax={dual.total_tax_depreciation} diff={dual.total_difference}')
                if not commit: raise _Rollback
        except _Rollback:
            print('FIXED_ASSET_COUNT_DUAL_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--commit', action='store_true'); asyncio.run(validate(parser.parse_args().commit))
if __name__ == '__main__': main()
