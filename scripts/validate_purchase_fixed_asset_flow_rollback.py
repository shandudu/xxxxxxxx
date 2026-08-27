"""Validate purchase receipt to fixed asset, invoice match and depreciation flow."""
from __future__ import annotations
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import FinancePeriodCreate, FixedAssetFromReceiptRequest
from backend.plugin.finance.service import finance_service
from backend.plugin.purchasing.model import SupplierReceipt

class _Rollback(Exception): pass

async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                receipt = await db.scalar(select(SupplierReceipt).where(SupplierReceipt.deleted == 0).order_by(SupplierReceipt.id.desc()))
                if not receipt: raise RuntimeError('supplier receipt missing')
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2100-01-PURCH-ASSET', start_date=date(2100,1,1), end_date=date(2100,1,31)))
                req = FixedAssetFromReceiptRequest(period_id=period.id, invoice_date=date(2100,1,2), due_date=date(2100,2,2), tax_rate=Decimal('0'), asset_name='采购设备自动资产', useful_life_months=60)
                asset = await finance_service.create_fixed_asset_from_receipt(db, receipt.id, req)
                same = await finance_service.create_fixed_asset_from_receipt(db, receipt.id, req)
                depreciation = await finance_service.run_fixed_asset_depreciation(db, period.id)
                if asset.id != same.id or not asset.ap_invoice_id or not asset.voucher_id or not depreciation.rows:
                    raise RuntimeError('purchase fixed asset flow validation failed')
                print(f'PURCHASE_FIXED_ASSET_OK receipt={receipt.id} asset={asset.id} ap_invoice={asset.ap_invoice_id} depreciation={depreciation.total_depreciation}')
                if not commit: raise _Rollback
        except _Rollback:
            print('PURCHASE_FIXED_ASSET_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--commit', action='store_true'); asyncio.run(validate(parser.parse_args().commit))
if __name__ == '__main__': main()
