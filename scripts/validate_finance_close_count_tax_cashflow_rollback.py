"""Validate finance close, tax ledger and cash-flow forecast transactions."""
from __future__ import annotations
import argparse
import asyncio
from datetime import date
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import FinancePeriodCreate, TaxInvoiceSyncRequest
from backend.plugin.finance.service import finance_service

class _Rollback(Exception): pass

async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2099-10-CLOSE', start_date=date(2099,10,1), end_date=date(2099,10,31)))
                tax = await finance_service.sync_tax_invoices(db, TaxInvoiceSyncRequest(period_id=period.id))
                forecast = await finance_service.cash_flow_forecast(db, period.id, rebuild=True)
                checks = await finance_service.closing_checks(db, period.id)
                if not isinstance(checks, list) or forecast.period_id != period.id:
                    raise RuntimeError('close/count/tax/cashflow validation failed')
                print(f'FINANCE_CLOSE_TAX_CASHFLOW_OK checks={len(checks)} tax={len(tax)} forecast={len(forecast.rows)}')
                if not commit: raise _Rollback
        except _Rollback:
            print('FINANCE_CLOSE_TAX_CASHFLOW_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--commit', action='store_true'); asyncio.run(validate(parser.parse_args().commit))
if __name__ == '__main__': main()
