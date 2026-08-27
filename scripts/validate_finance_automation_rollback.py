"""Validate automatic invoicing, three-way matching, plans and bank reconciliation."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.enums import BankDirection
from backend.plugin.finance.schema.finance import AutoInvoiceRequest, BankReconcileRequest, BankStatementCreate, SettlementCreate, ThreeWayMatchRequest
from backend.plugin.finance.service import finance_service
from backend.plugin.purchasing.model import PurchaseOrderLine, SupplierReceipt, SupplierReceiptLine
from backend.plugin.sales.model import Shipment


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                shipment = await db.scalar(select(Shipment).where(Shipment.deleted == 0).order_by(Shipment.id.desc()))
                receipt = await db.scalar(select(SupplierReceipt).where(SupplierReceipt.deleted == 0).order_by(SupplierReceipt.id.desc()))
                if not shipment or not receipt:
                    raise RuntimeError('demo shipment or supplier receipt missing')
                request = AutoInvoiceRequest(invoice_date=date(2099, 10, 1), due_date=date(2099, 10, 31), tax_rate=Decimal('0'))
                ar = await finance_service.auto_ar_invoice(db, shipment.id, request)
                ap = await finance_service.auto_ap_invoice(db, receipt.id, request)
                receipt_line = await db.scalar(select(SupplierReceiptLine).where(SupplierReceiptLine.supplier_receipt_id == receipt.id, SupplierReceiptLine.deleted == 0).order_by(SupplierReceiptLine.id))
                if not receipt_line:
                    raise RuntimeError('receipt line missing')
                po_line = await db.scalar(select(PurchaseOrderLine).where(PurchaseOrderLine.id == receipt_line.purchase_order_line_id, PurchaseOrderLine.deleted == 0))
                match = await finance_service.match_three_way(db, ThreeWayMatchRequest(ap_invoice_id=ap.id, purchase_order_line_id=po_line.id, supplier_receipt_line_id=receipt_line.id)) if po_line else None
                plans = await finance_service.payment_plans(db)
                reconciled = 0
                if ar.total_amount > 0:
                    ar_receipt = await finance_service.settle_ar(db, SettlementCreate(document_id=ar.id, amount=ar.total_amount, settlement_date=date(2099, 10, 5), reference_no='BANK-AR-AUTO'))
                    statement = await finance_service.create_bank_statement(db, BankStatementCreate(statement_no='BANK-ST-AR-AUTO', bank_account='1002', transaction_date=date(2099, 10, 5), direction=BankDirection.IN.value, amount=ar_receipt.amount, reference_no=ar_receipt.reference_no))
                    await finance_service.reconcile_bank(db, BankReconcileRequest(statement_id=statement.id, target_type='AR_RECEIPT', target_id=ar_receipt.id, amount=ar_receipt.amount)); reconciled += 1
                if ap.total_amount > 0:
                    ap_payment = await finance_service.settle_ap(db, SettlementCreate(document_id=ap.id, amount=ap.total_amount, settlement_date=date(2099, 10, 6), reference_no='BANK-AP-AUTO'))
                    statement = await finance_service.create_bank_statement(db, BankStatementCreate(statement_no='BANK-ST-AP-AUTO', bank_account='1002', transaction_date=date(2099, 10, 6), direction=BankDirection.OUT.value, amount=ap_payment.amount, reference_no=ap_payment.reference_no))
                    await finance_service.auto_reconcile_bank(db, statement.id); reconciled += 1
                if not ar.source_type or not ap.source_type or match is None or not plans or reconciled < 1:
                    raise RuntimeError('finance automation verification failed')
                print(f'FINANCE_AUTOMATION_OK ar={ar.total_amount} ap={ap.total_amount} plans={len(plans)} match={match.status} reconciled={reconciled}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('FINANCE_AUTOMATION_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    asyncio.run(validate(args.commit))


if __name__ == '__main__':
    main()
