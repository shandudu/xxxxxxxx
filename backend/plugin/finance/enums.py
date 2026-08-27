from enum import StrEnum


class FinancePeriodStatus(StrEnum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'


class FinanceDocumentStatus(StrEnum):
    OPEN = 'OPEN'
    PARTIAL = 'PARTIAL'
    PAID = 'PAID'
    CANCELLED = 'CANCELLED'


class VoucherStatus(StrEnum):
    DRAFT = 'DRAFT'
    POSTED = 'POSTED'
    REVERSED = 'REVERSED'


class VoucherSourceType(StrEnum):
    AR_INVOICE = 'AR_INVOICE'
    AP_INVOICE = 'AP_INVOICE'
    AR_RECEIPT = 'AR_RECEIPT'
    AP_PAYMENT = 'AP_PAYMENT'
    INVENTORY_VALUATION = 'INVENTORY_VALUATION'


class PaymentPlanDirection(StrEnum):
    AR = 'AR'
    AP = 'AP'


class PaymentPlanStatus(StrEnum):
    PLANNED = 'PLANNED'
    PARTIAL = 'PARTIAL'
    SETTLED = 'SETTLED'
    OVERDUE = 'OVERDUE'


class BankStatementStatus(StrEnum):
    UNMATCHED = 'UNMATCHED'
    PARTIAL = 'PARTIAL'
    MATCHED = 'MATCHED'
    IGNORED = 'IGNORED'


class BankDirection(StrEnum):
    IN = 'IN'
    OUT = 'OUT'


class ThreeWayMatchStatus(StrEnum):
    MATCHED = 'MATCHED'
    PRICE_VARIANCE = 'PRICE_VARIANCE'
    QUANTITY_VARIANCE = 'QUANTITY_VARIANCE'
    EXCEPTION = 'EXCEPTION'


class ClosingCheckStatus(StrEnum):
    PASS = 'PASS'
    BLOCK = 'BLOCK'


class InventoryCountStatus(StrEnum):
    DRAFT = 'DRAFT'
    COUNTING = 'COUNTING'
    POSTED = 'POSTED'
    CANCELLED = 'CANCELLED'


class TaxInvoiceDirection(StrEnum):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'


class TaxInvoiceStatus(StrEnum):
    REGISTERED = 'REGISTERED'
    CERTIFIED = 'CERTIFIED'
    VOIDED = 'VOIDED'


class CostCenterStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class BudgetStatus(StrEnum):
    DRAFT = 'DRAFT'
    APPROVED = 'APPROVED'
    CLOSED = 'CLOSED'


class ExpenseClaimStatus(StrEnum):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    PAID = 'PAID'


class BudgetAlertStatus(StrEnum):
    OPEN = 'OPEN'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    CLOSED = 'CLOSED'


class FixedAssetStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    TRANSFERRED = 'TRANSFERRED'
    RETIRED = 'RETIRED'
    SCRAPPED = 'SCRAPPED'


class FixedAssetTransactionType(StrEnum):
    ACQUISITION = 'ACQUISITION'
    TRANSFER = 'TRANSFER'
    MAINTENANCE = 'MAINTENANCE'
    DISPOSAL = 'DISPOSAL'
    DEPRECIATION = 'DEPRECIATION'
    COUNT_ADJUSTMENT = 'COUNT_ADJUSTMENT'


class FixedAssetCountStatus(StrEnum):
    DRAFT = 'DRAFT'
    COUNTING = 'COUNTING'
    POSTED = 'POSTED'
    CANCELLED = 'CANCELLED'


class FixedAssetCountVariance(StrEnum):
    NONE = 'NONE'
    MISSING = 'MISSING'
    LOCATION_MISMATCH = 'LOCATION_MISMATCH'
    DAMAGED = 'DAMAGED'


class FixedAssetCountApprovalStatus(StrEnum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'


class ValuationMethod(StrEnum):
    MOVING_AVERAGE = 'MOVING_AVERAGE'
