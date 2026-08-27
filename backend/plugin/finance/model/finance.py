from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.finance.enums import BankDirection, BankStatementStatus, ClosingCheckStatus, FinanceDocumentStatus, FinancePeriodStatus, FixedAssetCountApprovalStatus, InventoryCountStatus, PaymentPlanDirection, PaymentPlanStatus, TaxInvoiceDirection, TaxInvoiceStatus, ThreeWayMatchStatus, ValuationMethod, VoucherStatus


class FinancePeriod(Base):
    __tablename__ = 'erp_finance_period'
    __table_args__ = (
        sa.UniqueConstraint('period_code', 'deleted', name='uk_erp_finance_period_code'),
        sa.Index('idx_erp_finance_period_status', 'status'),
        {'comment': 'ERP finance accounting period'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_code: Mapped[str] = mapped_column(sa.String(20))
    start_date: Mapped[date] = mapped_column(sa.Date)
    end_date: Mapped[date] = mapped_column(sa.Date)
    status: Mapped[FinancePeriodStatus] = mapped_column(sa.String(20), default=FinancePeriodStatus.OPEN, server_default='OPEN')
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class InventoryValuation(Base):
    __tablename__ = 'erp_inventory_valuation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_inventory_valuation_period'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_erp_inventory_valuation_material'),
        sa.UniqueConstraint('period_id', 'material_id', 'deleted', name='uk_erp_inventory_valuation_material'),
        sa.Index('idx_erp_inventory_valuation_period', 'period_id'),
        {'comment': 'ERP moving-average inventory valuation by material and period'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    method: Mapped[ValuationMethod] = mapped_column(sa.String(30), default=ValuationMethod.MOVING_AVERAGE, server_default='MOVING_AVERAGE')
    opening_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    opening_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    receipt_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    receipt_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    issue_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    issue_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    closing_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    closing_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    unit_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    coverage_rate: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('0'), server_default='0')
    calculated_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class ARInvoice(Base):
    __tablename__ = 'erp_ar_invoice'
    __table_args__ = (
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_erp_ar_invoice_customer'),
        sa.UniqueConstraint('invoice_no', 'deleted', name='uk_erp_ar_invoice_no'),
        sa.UniqueConstraint('source_type', 'source_id', 'deleted', name='uk_erp_ar_invoice_source'),
        sa.Index('idx_erp_ar_invoice_customer_status', 'customer_id', 'status'),
        {'comment': 'ERP accounts receivable invoice'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    invoice_no: Mapped[str] = mapped_column(sa.String(100))
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    customer_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    customer_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    invoice_date: Mapped[date] = mapped_column(sa.Date)
    due_date: Mapped[date] = mapped_column(sa.Date)
    net_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    source_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    tax_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    paid_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[FinanceDocumentStatus] = mapped_column(sa.String(20), default=FinanceDocumentStatus.OPEN, server_default='OPEN')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ARReceipt(Base):
    __tablename__ = 'erp_ar_receipt'
    __table_args__ = (
        sa.ForeignKeyConstraint(['invoice_id'], ['erp_ar_invoice.id'], name='fk_erp_ar_receipt_invoice'),
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_erp_ar_receipt_customer'),
        sa.UniqueConstraint('receipt_no', 'deleted', name='uk_erp_ar_receipt_no'),
        sa.Index('idx_erp_ar_receipt_customer', 'customer_id'),
        {'comment': 'ERP customer receipt and settlement'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    receipt_no: Mapped[str] = mapped_column(sa.String(100))
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    customer_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    receipt_date: Mapped[date] = mapped_column(sa.Date)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    method: Mapped[str] = mapped_column(sa.String(30), default='BANK', server_default='BANK')
    reference_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class APInvoice(Base):
    __tablename__ = 'erp_ap_invoice'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_erp_ap_invoice_supplier'),
        sa.UniqueConstraint('invoice_no', 'deleted', name='uk_erp_ap_invoice_no'),
        sa.UniqueConstraint('source_type', 'source_id', 'deleted', name='uk_erp_ap_invoice_source'),
        sa.Index('idx_erp_ap_invoice_supplier_status', 'supplier_id', 'status'),
        {'comment': 'ERP accounts payable invoice'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    invoice_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    supplier_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    invoice_date: Mapped[date] = mapped_column(sa.Date)
    due_date: Mapped[date] = mapped_column(sa.Date)
    net_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    source_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    tax_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    paid_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[FinanceDocumentStatus] = mapped_column(sa.String(20), default=FinanceDocumentStatus.OPEN, server_default='OPEN')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class APPayment(Base):
    __tablename__ = 'erp_ap_payment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['invoice_id'], ['erp_ap_invoice.id'], name='fk_erp_ap_payment_invoice'),
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_erp_ap_payment_supplier'),
        sa.UniqueConstraint('payment_no', 'deleted', name='uk_erp_ap_payment_no'),
        sa.Index('idx_erp_ap_payment_supplier', 'supplier_id'),
        {'comment': 'ERP supplier payment and settlement'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    payment_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    payment_date: Mapped[date] = mapped_column(sa.Date)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    method: Mapped[str] = mapped_column(sa.String(30), default='BANK', server_default='BANK')
    reference_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class GLVoucher(Base):
    __tablename__ = 'erp_gl_voucher'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_gl_voucher_period'),
        sa.UniqueConstraint('voucher_no', 'deleted', name='uk_erp_gl_voucher_no'),
        sa.UniqueConstraint('source_type', 'source_id', 'deleted', name='uk_erp_gl_voucher_source'),
        sa.Index('idx_erp_gl_voucher_period_status', 'period_id', 'status'),
        {'comment': 'ERP general ledger voucher header'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    voucher_no: Mapped[str] = mapped_column(sa.String(100))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    voucher_date: Mapped[date] = mapped_column(sa.Date)
    source_type: Mapped[str] = mapped_column(sa.String(30))
    source_id: Mapped[int] = mapped_column(sa.BigInteger)
    summary: Mapped[str] = mapped_column(sa.String(250))
    total_debit: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    total_credit: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[VoucherStatus] = mapped_column(sa.String(20), default=VoucherStatus.POSTED, server_default='POSTED')
    posted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class GLVoucherLine(Base):
    __tablename__ = 'erp_gl_voucher_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_gl_voucher_line_header'),
        sa.Index('idx_erp_gl_voucher_line_voucher', 'voucher_id'),
        sa.Index('idx_erp_gl_voucher_line_account', 'account_code'),
        {'comment': 'ERP general ledger voucher lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    voucher_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    account_code: Mapped[str] = mapped_column(sa.String(40))
    account_name: Mapped[str] = mapped_column(sa.String(100))
    debit: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    credit: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    customer_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    supplier_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    description: Mapped[str | None] = mapped_column(sa.String(250), default=None)


class PaymentPlan(Base):
    __tablename__ = 'erp_payment_plan'
    __table_args__ = (
        sa.ForeignKeyConstraint(['ar_invoice_id'], ['erp_ar_invoice.id'], name='fk_erp_payment_plan_ar_invoice'),
        sa.ForeignKeyConstraint(['ap_invoice_id'], ['erp_ap_invoice.id'], name='fk_erp_payment_plan_ap_invoice'),
        sa.UniqueConstraint('direction', 'document_id', 'deleted', name='uk_erp_payment_plan_document'),
        sa.Index('idx_erp_payment_plan_due_status', 'due_date', 'status'),
        {'comment': 'ERP receivable and payable collection/payment plan'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    plan_no: Mapped[str] = mapped_column(sa.String(100))
    direction: Mapped[PaymentPlanDirection] = mapped_column(sa.String(10))
    document_id: Mapped[int] = mapped_column(sa.BigInteger)
    partner_id: Mapped[int] = mapped_column(sa.BigInteger)
    partner_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    due_date: Mapped[date] = mapped_column(sa.Date)
    planned_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    ar_invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    ap_invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    settled_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[PaymentPlanStatus] = mapped_column(sa.String(20), default=PaymentPlanStatus.PLANNED, server_default='PLANNED')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class BankStatement(Base):
    __tablename__ = 'erp_bank_statement'
    __table_args__ = (
        sa.UniqueConstraint('statement_no', 'deleted', name='uk_erp_bank_statement_no'),
        sa.Index('idx_erp_bank_statement_status_date', 'status', 'transaction_date'),
        {'comment': 'ERP imported bank statement transactions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    statement_no: Mapped[str] = mapped_column(sa.String(100))
    bank_account: Mapped[str] = mapped_column(sa.String(80))
    transaction_date: Mapped[date] = mapped_column(sa.Date)
    direction: Mapped[BankDirection] = mapped_column(sa.String(10))
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    counterparty_name: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    reference_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    description: Mapped[str | None] = mapped_column(sa.String(250), default=None)
    status: Mapped[BankStatementStatus] = mapped_column(sa.String(20), default=BankStatementStatus.UNMATCHED, server_default='UNMATCHED')
    imported_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class BankReconciliation(Base):
    __tablename__ = 'erp_bank_reconciliation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['statement_id'], ['erp_bank_statement.id'], name='fk_erp_bank_reconciliation_statement'),
        sa.UniqueConstraint('statement_id', 'target_type', 'target_id', 'deleted', name='uk_erp_bank_reconciliation_target'),
        sa.Index('idx_erp_bank_reconciliation_statement', 'statement_id'),
        {'comment': 'ERP bank statement to AR/AP settlement reconciliation'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    statement_id: Mapped[int] = mapped_column(sa.BigInteger)
    target_type: Mapped[str] = mapped_column(sa.String(30))
    target_id: Mapped[int] = mapped_column(sa.BigInteger)
    matched_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    matched_at: Mapped[datetime] = mapped_column(TimeZone)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ThreeWayMatch(Base):
    __tablename__ = 'erp_three_way_match'
    __table_args__ = (
        sa.ForeignKeyConstraint(['purchase_order_line_id'], ['erp_purchase_order_line.id'], name='fk_erp_three_way_match_po_line'),
        sa.ForeignKeyConstraint(['supplier_receipt_line_id'], ['erp_supplier_receipt_line.id'], name='fk_erp_three_way_match_receipt_line'),
        sa.ForeignKeyConstraint(['ap_invoice_id'], ['erp_ap_invoice.id'], name='fk_erp_three_way_match_ap_invoice'),
        sa.UniqueConstraint('purchase_order_line_id', 'supplier_receipt_line_id', 'ap_invoice_id', 'deleted', name='uk_erp_three_way_match_source'),
        sa.Index('idx_erp_three_way_match_status', 'status'),
        {'comment': 'ERP purchase order, receipt and supplier invoice three-way match'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    purchase_order_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_receipt_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    ap_invoice_id: Mapped[int] = mapped_column(sa.BigInteger)
    ordered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    received_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    invoiced_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    ordered_unit_price: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    invoiced_unit_price: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    quantity_variance: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    price_variance: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[ThreeWayMatchStatus] = mapped_column(sa.String(30), default=ThreeWayMatchStatus.MATCHED, server_default='MATCHED')
    matched_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FinanceClosingCheck(Base):
    __tablename__ = 'erp_finance_closing_check'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_finance_closing_check_period'),
        sa.UniqueConstraint('period_id', 'check_code', 'deleted', name='uk_erp_finance_closing_check_code'),
        sa.Index('idx_erp_finance_closing_check_period', 'period_id'),
        {'comment': 'ERP month-end closing checklist results'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    check_code: Mapped[str] = mapped_column(sa.String(50))
    check_name: Mapped[str] = mapped_column(sa.String(150))
    status: Mapped[ClosingCheckStatus] = mapped_column(sa.String(20))
    checked_at: Mapped[datetime] = mapped_column(TimeZone)
    blocking: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    detail: Mapped[str | None] = mapped_column(UniversalText, default=None)


class InventoryCountTask(Base):
    __tablename__ = 'erp_inventory_count_task'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_inventory_count_task_period'),
        sa.UniqueConstraint('task_no', 'deleted', name='uk_erp_inventory_count_task_no'),
        sa.Index('idx_erp_inventory_count_task_status', 'status'),
        {'comment': 'ERP physical inventory count task'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    task_no: Mapped[str] = mapped_column(sa.String(100))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[InventoryCountStatus] = mapped_column(sa.String(20), default=InventoryCountStatus.DRAFT, server_default='DRAFT')
    counted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    posted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class InventoryCountLine(Base):
    __tablename__ = 'erp_inventory_count_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['task_id'], ['erp_inventory_count_task.id'], name='fk_erp_inventory_count_line_task'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_erp_inventory_count_line_material'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_erp_inventory_count_line_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_erp_inventory_count_line_location'),
        sa.Index('idx_erp_inventory_count_line_task', 'task_id'),
        {'comment': 'ERP physical count line and variance'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    book_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    counted_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    variance_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    unit_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    variance_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    adjustment_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class TaxInvoiceLedger(Base):
    __tablename__ = 'erp_tax_invoice_ledger'
    __table_args__ = (
        sa.ForeignKeyConstraint(['ar_invoice_id'], ['erp_ar_invoice.id'], name='fk_erp_tax_invoice_ledger_ar'),
        sa.ForeignKeyConstraint(['ap_invoice_id'], ['erp_ap_invoice.id'], name='fk_erp_tax_invoice_ledger_ap'),
        sa.UniqueConstraint('invoice_no', 'deleted', name='uk_erp_tax_invoice_ledger_no'),
        sa.Index('idx_erp_tax_invoice_ledger_direction_date', 'direction', 'issue_date'),
        {'comment': 'ERP input/output tax invoice ledger'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    invoice_no: Mapped[str] = mapped_column(sa.String(100))
    direction: Mapped[TaxInvoiceDirection] = mapped_column(sa.String(10))
    partner_id: Mapped[int] = mapped_column(sa.BigInteger)
    partner_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    issue_date: Mapped[date] = mapped_column(sa.Date)
    net_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    tax_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    ar_invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    ap_invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    tax_rate: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('0'), server_default='0')
    status: Mapped[TaxInvoiceStatus] = mapped_column(sa.String(20), default=TaxInvoiceStatus.REGISTERED, server_default='REGISTERED')
    certification_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class CashFlowForecast(Base):
    __tablename__ = 'erp_cash_flow_forecast'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_cash_flow_forecast_period'),
        sa.UniqueConstraint('period_id', 'forecast_date', 'direction', 'category', 'source_type', 'source_id', 'deleted', name='uk_erp_cash_flow_forecast_source'),
        sa.Index('idx_erp_cash_flow_forecast_date_direction', 'forecast_date', 'direction'),
        {'comment': 'ERP expected cash inflow and outflow forecast'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    forecast_date: Mapped[date] = mapped_column(sa.Date)
    direction: Mapped[str] = mapped_column(sa.String(10))
    category: Mapped[str] = mapped_column(sa.String(50))
    source_type: Mapped[str] = mapped_column(sa.String(30))
    source_id: Mapped[int] = mapped_column(sa.BigInteger)
    expected_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    partner_name_snapshot: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    confidence: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('100'), server_default='100')
    status: Mapped[str] = mapped_column(sa.String(20), default='OPEN', server_default='OPEN')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class CostCenter(Base):
    __tablename__ = 'erp_cost_center'
    __table_args__ = (
        sa.UniqueConstraint('center_code', 'deleted', name='uk_erp_cost_center_code'),
        sa.Index('idx_erp_cost_center_status', 'status'),
        {'comment': 'ERP finance cost center master'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    center_code: Mapped[str] = mapped_column(sa.String(50))
    center_name: Mapped[str] = mapped_column(sa.String(150))
    center_type: Mapped[str] = mapped_column(sa.String(30))
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[str] = mapped_column(sa.String(20), default='ACTIVE', server_default='ACTIVE')
    manager_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FinanceBudget(Base):
    __tablename__ = 'erp_finance_budget'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_finance_budget_period'),
        sa.ForeignKeyConstraint(['cost_center_id'], ['erp_cost_center.id'], name='fk_erp_finance_budget_cost_center'),
        sa.UniqueConstraint('budget_no', 'deleted', name='uk_erp_finance_budget_no'),
        sa.Index('idx_erp_finance_budget_period_status', 'period_id', 'status'),
        {'comment': 'ERP finance budget header'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    budget_no: Mapped[str] = mapped_column(sa.String(100))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    budget_name: Mapped[str] = mapped_column(sa.String(200))
    budget_type: Mapped[str] = mapped_column(sa.String(30))
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[str] = mapped_column(sa.String(20), default='DRAFT', server_default='DRAFT')
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FinanceBudgetLine(Base):
    __tablename__ = 'erp_finance_budget_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['budget_id'], ['erp_finance_budget.id'], name='fk_erp_finance_budget_line_budget'),
        sa.UniqueConstraint('budget_id', 'account_code', 'category', 'deleted', name='uk_erp_finance_budget_line_key'),
        sa.Index('idx_erp_finance_budget_line_budget', 'budget_id'),
        {'comment': 'ERP finance budget detail and actual consumption'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    budget_id: Mapped[int] = mapped_column(sa.BigInteger)
    account_code: Mapped[str] = mapped_column(sa.String(40))
    category: Mapped[str] = mapped_column(sa.String(80))
    budget_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    consumed_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    warning_threshold: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('80'), server_default='80')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ExpenseClaim(Base):
    __tablename__ = 'erp_expense_claim'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_expense_claim_period'),
        sa.ForeignKeyConstraint(['cost_center_id'], ['erp_cost_center.id'], name='fk_erp_expense_claim_cost_center'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_expense_claim_voucher'),
        sa.UniqueConstraint('claim_no', 'deleted', name='uk_erp_expense_claim_no'),
        sa.Index('idx_erp_expense_claim_status_date', 'status', 'expense_date'),
        {'comment': 'ERP employee expense reimbursement claim'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    claim_no: Mapped[str] = mapped_column(sa.String(100))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    applicant_id: Mapped[int] = mapped_column(sa.BigInteger)
    expense_date: Mapped[date] = mapped_column(sa.Date)
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[str] = mapped_column(sa.String(20), default='DRAFT', server_default='DRAFT')
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    paid_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    rejection_reason: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ExpenseClaimLine(Base):
    __tablename__ = 'erp_expense_claim_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['claim_id'], ['erp_expense_claim.id'], name='fk_erp_expense_claim_line_claim'),
        sa.ForeignKeyConstraint(['budget_line_id'], ['erp_finance_budget_line.id'], name='fk_erp_expense_claim_line_budget'),
        sa.Index('idx_erp_expense_claim_line_claim', 'claim_id'),
        {'comment': 'ERP expense claim detail'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    claim_id: Mapped[int] = mapped_column(sa.BigInteger)
    category: Mapped[str] = mapped_column(sa.String(80))
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    tax_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    budget_line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    invoice_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)


class BudgetAlert(Base):
    __tablename__ = 'erp_budget_alert'
    __table_args__ = (
        sa.ForeignKeyConstraint(['budget_line_id'], ['erp_finance_budget_line.id'], name='fk_erp_budget_alert_line'),
        sa.Index('idx_erp_budget_alert_status_triggered', 'status', 'triggered_at'),
        {'comment': 'ERP budget execution threshold alert'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    budget_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    alert_type: Mapped[str] = mapped_column(sa.String(30))
    threshold: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4))
    budget_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    consumed_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    utilization_rate: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4))
    triggered_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[str] = mapped_column(sa.String(20), default='OPEN', server_default='OPEN')
    detail: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FixedAsset(Base):
    __tablename__ = 'erp_fixed_asset'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_fixed_asset_period'),
        sa.ForeignKeyConstraint(['cost_center_id'], ['erp_cost_center.id'], name='fk_erp_fixed_asset_cost_center'),
        sa.ForeignKeyConstraint(['ap_invoice_id'], ['erp_ap_invoice.id'], name='fk_erp_fixed_asset_ap_invoice'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_fixed_asset_voucher'),
        sa.UniqueConstraint('asset_no', 'deleted', name='uk_erp_fixed_asset_no'),
        sa.Index('idx_erp_fixed_asset_status_category', 'status', 'category'),
        {'comment': 'ERP fixed asset master and book value'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    asset_no: Mapped[str] = mapped_column(sa.String(100))
    asset_name: Mapped[str] = mapped_column(sa.String(200))
    category: Mapped[str] = mapped_column(sa.String(80))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    acquisition_date: Mapped[date] = mapped_column(sa.Date)
    original_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    useful_life_months: Mapped[int] = mapped_column()
    cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    barcode: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    serial_number: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    residual_rate: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('5'), server_default='5')
    residual_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    accumulated_depreciation: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    net_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    tax_accumulated_depreciation: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    tax_net_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[str] = mapped_column(sa.String(20), default='ACTIVE', server_default='ACTIVE')
    depreciation_method: Mapped[str] = mapped_column(sa.String(30), default='STRAIGHT_LINE', server_default='STRAIGHT_LINE')
    supplier_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    ap_invoice_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    disposed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FixedAssetTransaction(Base):
    __tablename__ = 'erp_fixed_asset_transaction'
    __table_args__ = (
        sa.ForeignKeyConstraint(['asset_id'], ['erp_fixed_asset.id'], name='fk_erp_fixed_asset_transaction_asset'),
        sa.ForeignKeyConstraint(['from_cost_center_id'], ['erp_cost_center.id'], name='fk_erp_fixed_asset_transaction_from_center'),
        sa.ForeignKeyConstraint(['to_cost_center_id'], ['erp_cost_center.id'], name='fk_erp_fixed_asset_transaction_to_center'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_fixed_asset_transaction_voucher'),
        sa.Index('idx_erp_fixed_asset_transaction_asset_date', 'asset_id', 'transaction_date'),
        {'comment': 'ERP fixed asset lifecycle transaction ledger'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    asset_id: Mapped[int] = mapped_column(sa.BigInteger)
    transaction_type: Mapped[str] = mapped_column(sa.String(30))
    transaction_date: Mapped[date] = mapped_column(sa.Date)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    from_cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    to_cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FixedAssetMaintenance(Base):
    __tablename__ = 'erp_fixed_asset_maintenance'
    __table_args__ = (
        sa.ForeignKeyConstraint(['asset_id'], ['erp_fixed_asset.id'], name='fk_erp_fixed_asset_maintenance_asset'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_fixed_asset_maintenance_voucher'),
        sa.Index('idx_erp_fixed_asset_maintenance_asset_date', 'asset_id', 'maintenance_date'),
        {'comment': 'ERP fixed asset maintenance record'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    asset_id: Mapped[int] = mapped_column(sa.BigInteger)
    maintenance_date: Mapped[date] = mapped_column(sa.Date)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    vendor_name: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class FixedAssetDepreciation(Base):
    __tablename__ = 'erp_fixed_asset_depreciation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['asset_id'], ['erp_fixed_asset.id'], name='fk_erp_fixed_asset_depreciation_asset'),
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_fixed_asset_depreciation_period'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_erp_fixed_asset_depreciation_voucher'),
        sa.UniqueConstraint('asset_id', 'period_id', 'deleted', name='uk_erp_fixed_asset_depreciation_period'),
        sa.Index('idx_erp_fixed_asset_depreciation_period', 'period_id'),
        {'comment': 'ERP fixed asset monthly depreciation posting'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    asset_id: Mapped[int] = mapped_column(sa.BigInteger)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    depreciation_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    accumulated_depreciation: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    net_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    posted_at: Mapped[datetime] = mapped_column(TimeZone)
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class FixedAssetTaxDepreciation(Base):
    __tablename__ = 'erp_fixed_asset_tax_depreciation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['asset_id'], ['erp_fixed_asset.id'], name='fk_erp_fixed_asset_tax_depreciation_asset'),
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_fixed_asset_tax_depreciation_period'),
        sa.UniqueConstraint('asset_id', 'period_id', 'deleted', name='uk_erp_fixed_asset_tax_depreciation_period'),
        sa.Index('idx_erp_fixed_asset_tax_depreciation_period', 'period_id'),
        {'comment': 'ERP tax depreciation ledger separated from book depreciation'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    asset_id: Mapped[int] = mapped_column(sa.BigInteger)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    depreciation_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    accumulated_depreciation: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    net_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    posted_at: Mapped[datetime] = mapped_column(TimeZone)
    tax_method: Mapped[str] = mapped_column(sa.String(30), default='STRAIGHT_LINE', server_default='STRAIGHT_LINE')


class FixedAssetCountTask(Base):
    __tablename__ = 'erp_fixed_asset_count_task'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_erp_fixed_asset_count_task_period'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['sys_user.id'], name='fk_erp_fixed_asset_count_task_user'),
        sa.UniqueConstraint('task_no', 'deleted', name='uk_erp_fixed_asset_count_task_no'),
        sa.Index('idx_erp_fixed_asset_count_task_status', 'status'),
        {'comment': 'ERP fixed asset physical count task'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    task_no: Mapped[str] = mapped_column(sa.String(100))
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[str] = mapped_column(sa.String(20), default='COUNTING', server_default='COUNTING')
    zone_code: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    counted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    posted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class FixedAssetCountLine(Base):
    __tablename__ = 'erp_fixed_asset_count_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['task_id'], ['erp_fixed_asset_count_task.id'], name='fk_erp_fixed_asset_count_line_task'),
        sa.ForeignKeyConstraint(['asset_id'], ['erp_fixed_asset.id'], name='fk_erp_fixed_asset_count_line_asset'),
        sa.ForeignKeyConstraint(['approved_by'], ['sys_user.id'], name='fk_erp_fixed_asset_count_line_approver'),
        sa.Index('idx_erp_fixed_asset_count_line_task', 'task_id'),
        {'comment': 'ERP fixed asset count result and book-to-physical variance'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    task_id: Mapped[int] = mapped_column(sa.BigInteger)
    asset_id: Mapped[int] = mapped_column(sa.BigInteger)
    barcode_snapshot: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    serial_snapshot: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    counted: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    observed_cost_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    variance_type: Mapped[str] = mapped_column(sa.String(30), default='NONE', server_default='NONE')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    evidence_photo: Mapped[str | None] = mapped_column(UniversalText, default=None)
    evidence_note: Mapped[str | None] = mapped_column(UniversalText, default=None)
    approval_status: Mapped[FixedAssetCountApprovalStatus] = mapped_column(sa.String(20), default=FixedAssetCountApprovalStatus.PENDING, server_default='PENDING')
    approved_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
