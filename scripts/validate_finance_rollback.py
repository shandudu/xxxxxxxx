"""Validate inventory valuation, AR/AP settlement, vouchers and finance dashboard."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.customer.model import Customer
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.enums import VoucherSourceType
from backend.plugin.finance.schema.finance import APInvoiceCreate, ARInvoiceCreate, FinancePeriodCreate, SettlementCreate, VoucherGenerateRequest
from backend.plugin.finance.service import finance_service
from backend.plugin.supplier.model import Supplier


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2099-11', start_date=date(2099, 11, 1), end_date=date(2099, 11, 30)))
                valuations = await finance_service.calculate_inventory_valuation(db, period.id)
                customer = await db.scalar(select(Customer).where(Customer.deleted == 0).order_by(Customer.id))
                supplier = await db.scalar(select(Supplier).where(Supplier.deleted == 0).order_by(Supplier.id))
                if not customer or not supplier:
                    raise RuntimeError('demo customer or supplier missing')
                ar = await finance_service.create_ar_invoice(db, ARInvoiceCreate(invoice_no='AR-DEMO-209911', customer_id=customer.id, invoice_date=date(2099, 11, 10), due_date=date(2099, 11, 30), net_amount=Decimal('1000'), total_amount=Decimal('1000')))
                ap = await finance_service.create_ap_invoice(db, APInvoiceCreate(invoice_no='AP-DEMO-209911', supplier_id=supplier.id, invoice_date=date(2099, 11, 10), due_date=date(2099, 11, 30), net_amount=Decimal('600'), total_amount=Decimal('600')))
                ar_receipt = await finance_service.settle_ar(db, SettlementCreate(document_id=ar.id, amount=Decimal('1000'), settlement_date=date(2099, 11, 15)))
                ap_payment = await finance_service.settle_ap(db, SettlementCreate(document_id=ap.id, amount=Decimal('600'), settlement_date=date(2099, 11, 15)))
                vouchers = []
                for source_type, source_id in ((VoucherSourceType.AR_INVOICE.value, ar.id), (VoucherSourceType.AP_INVOICE.value, ap.id), (VoucherSourceType.AR_RECEIPT.value, ar_receipt.id), (VoucherSourceType.AP_PAYMENT.value, ap_payment.id)):
                    vouchers.append(await finance_service.generate_voucher(db, VoucherGenerateRequest(period_id=period.id, source_type=source_type, source_id=source_id)))
                dashboard = await finance_service.dashboard(db, period.id)
                if not valuations or dashboard.revenue != Decimal('1000.000000') or dashboard.cogs != Decimal('0.000000') or any(v.total_debit != v.total_credit for v in vouchers):
                    raise RuntimeError('finance verification failed')
                print(f'FINANCE_RUN_OK valuations={len(valuations)} vouchers={len(vouchers)} gross_profit={dashboard.gross_profit}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('FINANCE_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
