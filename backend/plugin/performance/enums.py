from enum import StrEnum


class MetricGrain(StrEnum):
    DAY = 'DAY'
    WEEK = 'WEEK'
    MONTH = 'MONTH'


class TargetStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'
