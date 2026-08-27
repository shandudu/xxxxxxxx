from enum import StrEnum


class MpsPlanStatus(StrEnum):
    DRAFT = 'DRAFT'
    CONFIRMED = 'CONFIRMED'
    CLOSED = 'CLOSED'


class MpsDemandType(StrEnum):
    MANUAL = 'MANUAL'
    SALES_ORDER = 'SALES_ORDER'
    FORECAST = 'FORECAST'


class MrpRunStatus(StrEnum):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class PlannedOrderType(StrEnum):
    PURCHASE = 'PURCHASE'
    PRODUCTION = 'PRODUCTION'


class PlannedOrderStatus(StrEnum):
    PLANNED = 'PLANNED'
    FIRM = 'FIRM'
    RELEASED = 'RELEASED'
    CANCELLED = 'CANCELLED'
