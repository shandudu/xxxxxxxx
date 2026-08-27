from enum import StrEnum


class WorkOrderStatus(StrEnum):
    DRAFT = 'DRAFT'
    RELEASED = 'RELEASED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class WorkOrderOperationStatus(StrEnum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    SKIPPED = 'SKIPPED'


class MaterialDocumentStatus(StrEnum):
    POSTED = 'POSTED'


class ProductionExecutionStatus(StrEnum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class AndonEventType(StrEnum):
    STOPPAGE = 'STOPPAGE'
    MATERIAL_SHORTAGE = 'MATERIAL_SHORTAGE'
    QUALITY = 'QUALITY'


class AndonPriority(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class AndonStatus(StrEnum):
    OPEN = 'OPEN'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    IN_PROGRESS = 'IN_PROGRESS'
    BLOCKED = 'BLOCKED'
    RESOLVED = 'RESOLVED'
    CANCELLED = 'CANCELLED'
