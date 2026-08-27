from enum import StrEnum


class InspectionType(StrEnum):
    INCOMING = 'INCOMING'
    PROCESS = 'PROCESS'
    FINAL = 'FINAL'
    RETEST = 'RETEST'


class InspectionStatus(StrEnum):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class InspectionResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    PARTIAL = 'PARTIAL'


class NcrStatus(StrEnum):
    OPEN = 'OPEN'
    UNDER_REVIEW = 'UNDER_REVIEW'
    DISPOSED = 'DISPOSED'
    CLOSED = 'CLOSED'


class DispositionType(StrEnum):
    USE_AS_IS = 'USE_AS_IS'
    REWORK = 'REWORK'
    RETURN_TO_SUPPLIER = 'RETURN_TO_SUPPLIER'
    SCRAP = 'SCRAP'
    REINSPECT = 'REINSPECT'


class DispositionStatus(StrEnum):
    APPROVED = 'APPROVED'
    EXECUTED = 'EXECUTED'
    CANCELLED = 'CANCELLED'


class ReworkStatus(StrEnum):
    PLANNED = 'PLANNED'
    IN_PROGRESS = 'IN_PROGRESS'
    AWAITING_RETEST = 'AWAITING_RETEST'
    RELEASED = 'RELEASED'
    CANCELLED = 'CANCELLED'


class CapaStatus(StrEnum):
    OPEN = 'OPEN'
    ANALYSIS = 'ANALYSIS'
    ACTION = 'ACTION'
    VERIFYING = 'VERIFYING'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class CapaActionType(StrEnum):
    CONTAINMENT = 'CONTAINMENT'
    CORRECTIVE = 'CORRECTIVE'
    PREVENTIVE = 'PREVENTIVE'


class CapaActionStatus(StrEnum):
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    VERIFIED = 'VERIFIED'
    CANCELLED = 'CANCELLED'


class CapaVerificationResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'


class CustomerComplaintStatus(StrEnum):
    OPEN = 'OPEN'
    UNDER_REVIEW = 'UNDER_REVIEW'
    RMA_CREATED = 'RMA_CREATED'
    NCR_OPEN = 'NCR_OPEN'
    CAPA_IN_PROGRESS = 'CAPA_IN_PROGRESS'
    RESOLVED = 'RESOLVED'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class CustomerReturnStatus(StrEnum):
    DRAFT = 'DRAFT'
    AUTHORIZED = 'AUTHORIZED'
    RECEIVED = 'RECEIVED'
    INSPECTED = 'INSPECTED'
    RESOLVED = 'RESOLVED'
    CLOSED = 'CLOSED'
    CANCELLED = 'CANCELLED'


class CustomerReturnResolution(StrEnum):
    REFUND = 'REFUND'
    REPLACEMENT = 'REPLACEMENT'
    REPAIR = 'REPAIR'
    SCRAP = 'SCRAP'
    NO_DEFECT = 'NO_DEFECT'


class AfterSalesExecutionStatus(StrEnum):
    DRAFT = 'DRAFT'
    APPROVED = 'APPROVED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class AfterSalesAuditAction(StrEnum):
    CREATED = 'CREATED'
    APPROVED = 'APPROVED'
    STARTED = 'STARTED'
    STOCK_POSTED = 'STOCK_POSTED'
    REPAIR_TASK_CREATED = 'REPAIR_TASK_CREATED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class AfterSalesRepairTaskStatus(StrEnum):
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class SlaEntityType(StrEnum):
    NCR = 'NCR'
    CAPA = 'CAPA'
    COMPLAINT = 'COMPLAINT'
    RMA = 'RMA'
    AFTER_SALES = 'AFTER_SALES'


class SlaAlertStatus(StrEnum):
    OPEN = 'OPEN'
    WARNING = 'WARNING'
    OVERDUE = 'OVERDUE'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    CLOSED = 'CLOSED'


class InspectionValueType(StrEnum):
    NUMERIC = 'NUMERIC'
    BOOLEAN = 'BOOLEAN'
    TEXT = 'TEXT'


class QualityConfigStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class InspectionTemplateStatus(StrEnum):
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
