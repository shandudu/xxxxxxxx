from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.finance.enums import FinancePeriodStatus, VoucherStatus


class FinancePeriodCreate(SchemaBase):
    period_code: str = Field(min_length=4, max_length=20)
    start_date: date
    end_date: date
    currency: str = Field(default='CNY', min_length=3, max_length=10)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_dates(self) -> 'FinancePeriodCreate':
        if self.end_date < self.start_date:
            raise ValueError('end_date must not be before start_date')
        return self


class FinancePeriodDetail(FinancePeriodCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: FinancePeriodStatus
    closed_at: datetime | None = None


class InventoryValuationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    period_id: int
    material_id: int
    material_code_snapshot: str
    material_name_snapshot: str
    method: str
    opening_quantity: Decimal
    opening_value: Decimal
    receipt_quantity: Decimal
    receipt_value: Decimal
    issue_quantity: Decimal
    issue_value: Decimal
    closing_quantity: Decimal
    closing_value: Decimal
    unit_cost: Decimal
    coverage_rate: Decimal


class ARInvoiceCreate(SchemaBase):
    invoice_no: str = Field(min_length=3, max_length=100)
    customer_id: int = Field(ge=1)
    invoice_date: date
    due_date: date
    net_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    total_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    tax_amount: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    source_type: str | None = Field(default=None, max_length=30)
    source_id: int | None = Field(default=None, ge=1)
    source_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_total(self) -> 'ARInvoiceCreate':
        if self.total_amount != self.net_amount + self.tax_amount:
            raise ValueError('total_amount must equal net_amount plus tax_amount')
        return self


class APInvoiceCreate(SchemaBase):
    invoice_no: str = Field(min_length=3, max_length=100)
    supplier_id: int = Field(ge=1)
    invoice_date: date
    due_date: date
    net_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    total_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    tax_amount: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    source_type: str | None = Field(default=None, max_length=30)
    source_id: int | None = Field(default=None, ge=1)
    source_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_total(self) -> 'APInvoiceCreate':
        if self.total_amount != self.net_amount + self.tax_amount:
            raise ValueError('total_amount must equal net_amount plus tax_amount')
        return self


class SettlementCreate(SchemaBase):
    document_id: int = Field(ge=1)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    settlement_date: date
    method: str = Field(default='BANK', max_length=30)
    reference_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)


class AutoInvoiceRequest(SchemaBase):
    due_date: date
    invoice_date: date
    tax_rate: Decimal = Field(default=Decimal('0'), ge=0, le=100, max_digits=8, decimal_places=4)
    invoice_no: str | None = Field(default=None, max_length=100)


class ThreeWayMatchRequest(SchemaBase):
    ap_invoice_id: int = Field(ge=1)
    purchase_order_line_id: int = Field(ge=1)
    supplier_receipt_line_id: int = Field(ge=1)


class BankStatementCreate(SchemaBase):
    statement_no: str = Field(min_length=3, max_length=100)
    bank_account: str = Field(min_length=1, max_length=80)
    transaction_date: date
    direction: str = Field(pattern='^(IN|OUT)$')
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    counterparty_name: str | None = Field(default=None, max_length=200)
    reference_no: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=250)


class BankReconcileRequest(SchemaBase):
    statement_id: int = Field(ge=1)
    target_type: str = Field(pattern='^(AR_RECEIPT|AP_PAYMENT)$')
    target_id: int = Field(ge=1)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class PaymentPlanDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_no: str
    direction: str
    document_id: int
    partner_id: int
    partner_name_snapshot: str
    due_date: date
    planned_amount: Decimal
    settled_amount: Decimal
    status: str


class ThreeWayMatchDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    purchase_order_line_id: int
    supplier_receipt_line_id: int
    ap_invoice_id: int
    ordered_quantity: Decimal
    received_quantity: Decimal
    invoiced_quantity: Decimal
    ordered_unit_price: Decimal
    invoiced_unit_price: Decimal
    quantity_variance: Decimal
    price_variance: Decimal
    status: str


class BankStatementDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    statement_no: str
    bank_account: str
    transaction_date: date
    direction: str
    amount: Decimal
    counterparty_name: str | None = None
    reference_no: str | None = None
    description: str | None = None
    status: str


class VoucherGenerateRequest(SchemaBase):
    period_id: int = Field(ge=1)
    source_type: str = Field(min_length=3, max_length=30)
    source_id: int = Field(ge=1)


class VoucherLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    line_no: int
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    description: str | None = None


class VoucherDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    voucher_no: str
    period_id: int
    voucher_date: date
    source_type: str
    source_id: int
    summary: str
    total_debit: Decimal
    total_credit: Decimal
    status: VoucherStatus
    posted_at: datetime | None = None
    lines: list[VoucherLineDetail] = Field(default_factory=list)


class FinanceDashboard(SchemaBase):
    period_id: int | None = None
    period_code: str | None = None
    inventory_value: Decimal
    accounts_receivable: Decimal
    overdue_receivable: Decimal
    accounts_payable: Decimal
    overdue_payable: Decimal
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_rate: Decimal
    cash_in: Decimal
    cash_out: Decimal
    voucher_count: int


class ClosingCheckDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    period_id: int
    check_code: str
    check_name: str
    status: str
    blocking: bool
    detail: str | None = None
    checked_at: datetime


class InventoryCountLineCreate(SchemaBase):
    material_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    counted_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class InventoryCountCreate(SchemaBase):
    period_id: int = Field(ge=1)
    warehouse_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)
    lines: list[InventoryCountLineCreate] = Field(min_length=1)


class InventoryCountLineDetail(InventoryCountLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    book_quantity: Decimal
    variance_quantity: Decimal
    unit_cost: Decimal
    variance_value: Decimal
    adjustment_transaction_id: int | None = None


class InventoryCountDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_no: str
    period_id: int
    warehouse_id: int | None
    status: str
    counted_at: datetime | None
    posted_at: datetime | None
    remark: str | None
    lines: list[InventoryCountLineDetail] = Field(default_factory=list)


class TaxInvoiceSyncRequest(SchemaBase):
    period_id: int = Field(ge=1)


class TaxInvoiceDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_no: str
    direction: str
    partner_id: int
    partner_name_snapshot: str
    issue_date: date
    tax_rate: Decimal
    net_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    certification_no: str | None = None
    ar_invoice_id: int | None = None
    ap_invoice_id: int | None = None


class CashFlowForecastRow(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    period_id: int
    forecast_date: date
    direction: str
    category: str
    source_type: str
    source_id: int
    partner_name_snapshot: str | None
    expected_amount: Decimal
    confidence: Decimal
    status: str


class CashFlowForecastSummary(SchemaBase):
    period_id: int
    inflow: Decimal
    outflow: Decimal
    net_cash_flow: Decimal
    rows: list[CashFlowForecastRow] = Field(default_factory=list)


class CostCenterCreate(SchemaBase):
    center_code: str = Field(min_length=2, max_length=50)
    center_name: str = Field(min_length=1, max_length=150)
    center_type: str = Field(default='DEPARTMENT', max_length=30)
    parent_id: int | None = Field(default=None, ge=1)
    manager_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)


class CostCenterDetail(CostCenterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str


class BudgetLineCreate(SchemaBase):
    account_code: str = Field(min_length=1, max_length=40)
    category: str = Field(min_length=1, max_length=80)
    budget_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    warning_threshold: Decimal = Field(default=Decimal('80'), ge=0, le=100, max_digits=8, decimal_places=4)
    remark: str | None = Field(default=None, max_length=500)


class BudgetCreate(SchemaBase):
    period_id: int = Field(ge=1)
    budget_name: str = Field(min_length=1, max_length=200)
    budget_type: str = Field(default='OPERATING', max_length=30)
    cost_center_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)
    lines: list[BudgetLineCreate] = Field(min_length=1)


class BudgetLineDetail(BudgetLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    budget_id: int
    consumed_amount: Decimal


class BudgetDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    budget_no: str
    period_id: int
    budget_name: str
    budget_type: str
    total_amount: Decimal
    cost_center_id: int | None
    status: str
    approved_at: datetime | None
    remark: str | None
    lines: list[BudgetLineDetail] = Field(default_factory=list)


class ExpenseLineCreate(SchemaBase):
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    tax_amount: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    budget_line_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=500)
    invoice_no: str | None = Field(default=None, max_length=100)


class ExpenseClaimCreate(SchemaBase):
    period_id: int = Field(ge=1)
    applicant_id: int = Field(ge=1)
    expense_date: date
    cost_center_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    lines: list[ExpenseLineCreate] = Field(min_length=1)


class ExpenseLineDetail(ExpenseLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    claim_id: int


class ExpenseClaimDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    claim_no: str
    period_id: int
    applicant_id: int
    expense_date: date
    total_amount: Decimal
    cost_center_id: int | None
    status: str
    description: str | None
    approved_at: datetime | None
    paid_at: datetime | None
    voucher_id: int | None
    lines: list[ExpenseLineDetail] = Field(default_factory=list)


class BudgetAlertDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    budget_line_id: int
    alert_type: str
    threshold: Decimal
    budget_amount: Decimal
    consumed_amount: Decimal
    utilization_rate: Decimal
    triggered_at: datetime
    status: str
    detail: str | None


class FixedAssetCreate(SchemaBase):
    period_id: int = Field(ge=1)
    asset_name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    acquisition_date: date
    original_value: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    useful_life_months: int = Field(gt=0, le=1200)
    barcode: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    residual_rate: Decimal = Field(default=Decimal('5'), ge=0, le=100, max_digits=8, decimal_places=4)
    cost_center_id: int | None = Field(default=None, ge=1)
    supplier_id: int | None = Field(default=None, ge=1)
    source_type: str | None = Field(default=None, max_length=30)
    source_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)


class FixedAssetFromReceiptRequest(SchemaBase):
    period_id: int = Field(ge=1)
    invoice_date: date
    due_date: date
    tax_rate: Decimal = Field(default=Decimal('0'), ge=0, le=100, max_digits=8, decimal_places=4)
    asset_name: str = Field(min_length=1, max_length=200)
    category: str = Field(default='PRODUCTION_EQUIPMENT', max_length=80)
    useful_life_months: int = Field(gt=0, le=1200)
    residual_rate: Decimal = Field(default=Decimal('5'), ge=0, le=100, max_digits=8, decimal_places=4)
    cost_center_id: int | None = Field(default=None, ge=1)
    invoice_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)


class FixedAssetDetail(FixedAssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_no: str
    residual_value: Decimal
    accumulated_depreciation: Decimal
    net_value: Decimal
    tax_accumulated_depreciation: Decimal
    tax_net_value: Decimal
    status: str
    depreciation_method: str
    ap_invoice_id: int | None
    voucher_id: int | None
    disposed_at: datetime | None


class FixedAssetTransferRequest(SchemaBase):
    target_cost_center_id: int = Field(ge=1)
    transfer_date: date
    remark: str | None = Field(default=None, max_length=500)


class FixedAssetMaintenanceCreate(SchemaBase):
    maintenance_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    vendor_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class FixedAssetMaintenanceDetail(FixedAssetMaintenanceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    voucher_id: int | None


class FixedAssetDisposeRequest(SchemaBase):
    disposal_date: date
    disposal_amount: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    reason: str | None = Field(default=None, max_length=500)


class FixedAssetDepreciationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    period_id: int
    depreciation_amount: Decimal
    accumulated_depreciation: Decimal
    net_value: Decimal
    posted_at: datetime
    voucher_id: int | None


class FixedAssetDepreciationSummary(SchemaBase):
    period_id: int
    asset_count: int
    total_depreciation: Decimal
    rows: list[FixedAssetDepreciationDetail] = Field(default_factory=list)


class FixedAssetCountLineCreate(SchemaBase):
    asset_id: int = Field(ge=1)
    counted: bool = True
    observed_cost_center_id: int | None = Field(default=None, ge=1)
    variance_type: str = Field(default='NONE', max_length=30)
    remark: str | None = Field(default=None, max_length=500)
    evidence_photo: str | None = Field(default=None, max_length=2_000_000)
    evidence_note: str | None = Field(default=None, max_length=2000)


class FixedAssetCountCreate(SchemaBase):
    period_id: int = Field(ge=1)
    zone_code: str | None = Field(default=None, max_length=80)
    assigned_user_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)
    lines: list[FixedAssetCountLineCreate] = Field(min_length=1)


class FixedAssetCountLineDetail(FixedAssetCountLineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    barcode_snapshot: str | None
    serial_snapshot: str | None
    approval_status: str
    approved_by: int | None
    approved_at: datetime | None


class FixedAssetCountDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_no: str
    period_id: int
    status: str
    zone_code: str | None
    assigned_user_id: int | None
    counted_at: datetime | None
    posted_at: datetime | None
    remark: str | None
    lines: list[FixedAssetCountLineDetail] = Field(default_factory=list)


class FixedAssetCountScanRequest(SchemaBase):
    """移动端扫码盘点请求。code 支持资产条码或序列号。"""

    code: str = Field(min_length=1, max_length=120)
    counted: bool = True
    observed_cost_center_id: int | None = Field(default=None, ge=1)
    variance_type: str = Field(default='NONE', max_length=30)
    remark: str | None = Field(default=None, max_length=500)
    evidence_photo: str | None = Field(default=None, max_length=2_000_000)
    evidence_note: str | None = Field(default=None, max_length=2000)


class FixedAssetCountApprovalRequest(SchemaBase):
    status: str = Field(pattern='^(APPROVED|REJECTED)$')
    evidence_photo: str | None = Field(default=None, max_length=2_000_000)
    evidence_note: str | None = Field(default=None, max_length=2000)


class FixedAssetCountScanResult(SchemaBase):
    task_id: int
    asset: FixedAssetDetail
    line: FixedAssetCountLineDetail
    is_new: bool


class FixedAssetDualDepreciationDetail(SchemaBase):
    asset_id: int
    book_depreciation_amount: Decimal
    book_accumulated_depreciation: Decimal
    book_net_value: Decimal
    tax_depreciation_amount: Decimal
    tax_accumulated_depreciation: Decimal
    tax_net_value: Decimal
    book_tax_difference: Decimal
    book_voucher_id: int | None


class FixedAssetDualDepreciationSummary(SchemaBase):
    period_id: int
    asset_count: int
    total_book_depreciation: Decimal
    total_tax_depreciation: Decimal
    total_difference: Decimal
    rows: list[FixedAssetDualDepreciationDetail] = Field(default_factory=list)
