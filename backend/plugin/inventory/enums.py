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
