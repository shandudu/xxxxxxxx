from enum import StrEnum


class ConfigStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class SchedulingDirection(StrEnum):
    FORWARD = 'FORWARD'
    BACKWARD = 'BACKWARD'


class ScheduleStatus(StrEnum):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    PUBLISHED = 'PUBLISHED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class OperationScheduleStatus(StrEnum):
    PLANNED = 'PLANNED'
    PUBLISHED = 'PUBLISHED'
    DISPATCHED = 'DISPATCHED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class DispatchStatus(StrEnum):
    DISPATCHED = 'DISPATCHED'
    ACCEPTED = 'ACCEPTED'
    STARTED = 'STARTED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class ShopfloorStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class TeamMemberRole(StrEnum):
    LEADER = 'LEADER'
    OPERATOR = 'OPERATOR'
    QUALITY = 'QUALITY'
    MATERIAL = 'MATERIAL'
    OTHER = 'OTHER'


class WorkstationSessionStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'


class QualificationStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    SUSPENDED = 'SUSPENDED'
    REVOKED = 'REVOKED'


class RosterStatus(StrEnum):
    PLANNED = 'PLANNED'
    CONFIRMED = 'CONFIRMED'
    CANCELLED = 'CANCELLED'
