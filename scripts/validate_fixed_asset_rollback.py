"""Validate fixed asset lifecycle and idempotent monthly depreciation posting."""
from __future__ import annotations
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import CostCenterCreate, FinancePeriodCreate, FixedAssetCreate, FixedAssetMaintenanceCreate, FixedAssetTransferRequest
from backend.plugin.finance.service import finance_service

class _Rollback(Exception): pass

async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2099-12-ASSET', start_date=date(2099,12,1), end_date=date(2099,12,31)))
                center = await finance_service.create_cost_center(db, CostCenterCreate(center_code='CC-ASSET', center_name='资产成本中心'))
                asset = await finance_service.create_fixed_asset(db, FixedAssetCreate(period_id=period.id, asset_name='演示设备', category='生产设备', acquisition_date=date(2099,12,1), original_value=Decimal('1200'), useful_life_months=12, cost_center_id=center.id))
                await finance_service.add_fixed_asset_maintenance(db, asset.id, FixedAssetMaintenanceCreate(maintenance_date=date(2099,12,5), amount=Decimal('50'), vendor_name='维修供应商'))
                depreciation = await finance_service.run_fixed_asset_depreciation(db, period.id)
                again = await finance_service.run_fixed_asset_depreciation(db, period.id)
                asset = await finance_service._fixed_asset_detail(db, asset.id)
                if depreciation.total_depreciation != Decimal('95.000000') or again.total_depreciation != depreciation.total_depreciation or asset.net_value >= asset.original_value:
                    raise RuntimeError('fixed asset validation failed')
                print(f'FIXED_ASSET_OK asset={asset.asset_no} depreciation={depreciation.total_depreciation} vouchers={len(depreciation.rows)} net={asset.net_value}')
                if not commit: raise _Rollback
        except _Rollback:
            print('FIXED_ASSET_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--commit', action='store_true'); asyncio.run(validate(parser.parse_args().commit))
if __name__ == '__main__': main()
