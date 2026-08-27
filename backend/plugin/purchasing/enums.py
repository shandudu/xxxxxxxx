from enum import StrEnum


class PurchaseOrderStatus(StrEnum):
    DRAFT = 'DRAFT'
    CONFIRMED = 'CONFIRMED'
    PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED'
    RECEIVED = 'RECEIVED'
    CANCELLED = 'CANCELLED'


class SupplierReceiptStatus(StrEnum):
    POSTED = 'POSTED'


class SupplierReturnStatus(StrEnum):
    POSTED = 'POSTED'


class PurchaseDeliveryPerformanceStatus(StrEnum):
    OPEN = 'OPEN'
    OTIF = 'OTIF'
    LATE = 'LATE'
    LATE_AND_NOT_IN_FULL = 'LATE_AND_NOT_IN_FULL'


class PurchaseDelayReason(StrEnum):
    SHORTAGE_IMPACT = 'SHORTAGE_IMPACT'
    SUPPLIER = 'SUPPLIER'
