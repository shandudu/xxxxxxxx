from enum import StrEnum


class PackagingSpecStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class PackagingTaskStatus(StrEnum):
    DRAFT = 'DRAFT'
    RELEASED = 'RELEASED'
    IN_PROGRESS = 'IN_PROGRESS'
    PACKED = 'PACKED'
    INSPECTING = 'INSPECTING'
    RELEASED_TO_STOCK = 'RELEASED_TO_STOCK'
    CLOSED = 'CLOSED'
    SUSPENDED = 'SUSPENDED'
    CANCELLED = 'CANCELLED'


class HandlingUnitType(StrEnum):
    INNER = 'INNER'
    CARTON = 'CARTON'
    PALLET = 'PALLET'


class HandlingUnitStatus(StrEnum):
    OPEN = 'OPEN'
    SEALED = 'SEALED'
    QUALITY_HOLD = 'QUALITY_HOLD'
    RELEASED = 'RELEASED'
    STORED = 'STORED'
    VOIDED = 'VOIDED'


class PackagingInspectionResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'


class PackagingScanType(StrEnum):
    LOT = 'LOT'
    SERIAL = 'SERIAL'


class WeightCheckResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    NOT_REQUIRED = 'NOT_REQUIRED'
