from backend.common.enums import StrEnum


class OperationStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class OperationType(StrEnum):
    PROCESS = 'PROCESS'
    ASSEMBLY = 'ASSEMBLY'
    INSPECTION = 'INSPECTION'
    PACKAGING = 'PACKAGING'
    TRANSFER = 'TRANSFER'
    OTHER = 'OTHER'


class WorkCenterStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class WorkCenterType(StrEnum):
    MACHINE_GROUP = 'MACHINE_GROUP'
    PRODUCTION_LINE = 'PRODUCTION_LINE'
    MANUAL = 'MANUAL'
    CELL = 'CELL'
    INSPECTION = 'INSPECTION'
    PACKAGING = 'PACKAGING'
    OTHER = 'OTHER'


class RoutingStatus(StrEnum):
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class RoutingType(StrEnum):
    STANDARD = 'STANDARD'
    REWORK = 'REWORK'
    TRIAL = 'TRIAL'


class RunTimeUnit(StrEnum):
    MIN_PER_BASE_QTY = 'MIN_PER_BASE_QTY'
    HOUR_PER_BASE_QTY = 'HOUR_PER_BASE_QTY'
    SEC_PER_BASE_QTY = 'SEC_PER_BASE_QTY'
