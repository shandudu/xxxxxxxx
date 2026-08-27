from backend.common.enums import StrEnum


class TraceRuleType(StrEnum):
    LOT = 'LOT'
    SERIAL = 'SERIAL'


class TraceRuleStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class SequenceResetType(StrEnum):
    NEVER = 'NEVER'
    YEARLY = 'YEARLY'
    MONTHLY = 'MONTHLY'
    DAILY = 'DAILY'


class LotType(StrEnum):
    SUPPLIER = 'SUPPLIER'
    INTERNAL = 'INTERNAL'
    WIP = 'WIP'
    FINISHED = 'FINISHED'
    REWORK = 'REWORK'
    OTHER = 'OTHER'


class LotSourceType(StrEnum):
    PURCHASE_RECEIPT = 'PURCHASE_RECEIPT'
    WORK_ORDER = 'WORK_ORDER'
    MANUAL = 'MANUAL'
    LOT_SPLIT = 'LOT_SPLIT'
    LOT_MERGE = 'LOT_MERGE'
    REWORK = 'REWORK'


class LotStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    HOLD = 'HOLD'
    CONSUMED = 'CONSUMED'
    CLOSED = 'CLOSED'
    DISABLED = 'DISABLED'


class QualityStatus(StrEnum):
    UNINSPECTED = 'UNINSPECTED'
    PASS = 'PASS'
    FAIL = 'FAIL'
    HOLD = 'HOLD'


class SerialStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    HOLD = 'HOLD'
    SCRAPPED = 'SCRAPPED'
    CONSUMED = 'CONSUMED'
    SHIPPED = 'SHIPPED'
    DISABLED = 'DISABLED'


class TraceObjectType(StrEnum):
    LOT = 'LOT'
    SERIAL = 'SERIAL'


class TraceRelationType(StrEnum):
    CONSUMED_TO = 'CONSUMED_TO'
    PRODUCED_FROM = 'PRODUCED_FROM'
    SPLIT_TO = 'SPLIT_TO'
    MERGED_TO = 'MERGED_TO'
    PACKED_INTO = 'PACKED_INTO'
    REWORK_TO = 'REWORK_TO'

