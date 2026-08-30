from enum import StrEnum


class StockTransactionType(StrEnum):
    RECEIPT = 'RECEIPT'
    ISSUE = 'ISSUE'
    RETURN = 'RETURN'
    PRODUCTION_RECEIPT = 'PRODUCTION_RECEIPT'
    SHIPMENT = 'SHIPMENT'
    TRANSFER_OUT = 'TRANSFER_OUT'
    TRANSFER_IN = 'TRANSFER_IN'
    ADJUSTMENT = 'ADJUSTMENT'
    SCRAP = 'SCRAP'
    PURCHASE_RETURN = 'PURCHASE_RETURN'
    CUSTOMER_RETURN = 'CUSTOMER_RETURN'


class StockMovementStatus(StrEnum):
    DRAFT = 'DRAFT'
    POSTED = 'POSTED'
    CANCELLED = 'CANCELLED'


class InventoryPolicyStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class ReplenishmentStatus(StrEnum):
    SUGGESTED = 'SUGGESTED'
    FIRM = 'FIRM'
    RELEASED = 'RELEASED'
    CANCELLED = 'CANCELLED'


class ReplenishmentOrderType(StrEnum):
    PURCHASE = 'PURCHASE'
    PRODUCTION = 'PRODUCTION'


class ReplenishmentAlertLevel(StrEnum):
    SHORTAGE = 'SHORTAGE'
    REORDER = 'REORDER'
    COVERED = 'COVERED'


class ShelfLifePolicyStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class ExpiryAlertLevel(StrEnum):
    WARNING = 'WARNING'
    CRITICAL = 'CRITICAL'
    EXPIRED = 'EXPIRED'


class ExpiryAlertStatus(StrEnum):
    OPEN = 'OPEN'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    CLOSED = 'CLOSED'


class LotHoldReason(StrEnum):
    EXPIRED = 'EXPIRED'
    RECALL = 'RECALL'
    MANUAL = 'MANUAL'


class LotHoldStatus(StrEnum):
    OPEN = 'OPEN'
    AWAITING_RETEST = 'AWAITING_RETEST'
    RELEASED = 'RELEASED'
    SCRAPPED = 'SCRAPPED'


class LotRecallStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class RecallItemType(StrEnum):
    INVENTORY_LOT = 'INVENTORY_LOT'
    SHIPMENT = 'SHIPMENT'


class RecallItemStatus(StrEnum):
    PENDING = 'PENDING'
    QUARANTINED = 'QUARANTINED'
    NOTIFIED = 'NOTIFIED'
    RETURNED = 'RETURNED'
    CLOSED = 'CLOSED'
