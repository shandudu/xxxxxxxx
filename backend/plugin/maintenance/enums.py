from enum import StrEnum


class MaintenancePlanType(StrEnum):
    INSPECTION = 'INSPECTION'
    PREVENTIVE = 'PREVENTIVE'


class CycleUnit(StrEnum):
    DAY = 'DAY'
    WEEK = 'WEEK'
    MONTH = 'MONTH'


class PlanStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class TaskStatus(StrEnum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class TaskResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    NA = 'NA'


class FaultLevel(StrEnum):
    MINOR = 'MINOR'
    MAJOR = 'MAJOR'
    CRITICAL = 'CRITICAL'


class RepairStatus(StrEnum):
    REPORTED = 'REPORTED'
    ASSIGNED = 'ASSIGNED'
    IN_REPAIR = 'IN_REPAIR'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class DowntimeCategory(StrEnum):
    PLANNED = 'PLANNED'
    UNPLANNED = 'UNPLANNED'


class DowntimeStatus(StrEnum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class DowntimeSourceType(StrEnum):
    MANUAL = 'MANUAL'
    INSPECTION = 'INSPECTION'
    MAINTENANCE = 'MAINTENANCE'
    REPAIR = 'REPAIR'
