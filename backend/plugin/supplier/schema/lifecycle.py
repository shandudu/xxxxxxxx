from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.plugin.supplier.enums import (
    SupplierAuditResult,
    SupplierAuditStatus,
    SupplierAuditType,
    SupplierAvlStatus,
    SupplierPpapStatus,
    SupplierQualificationStatus,
    SupplierReviewDecision,
    SupplierReviewStatus,
    SupplierSampleStatus,
)


class CreateQualificationApplication(SchemaBase):
    supplier_id: int = Field(ge=1)
    requested_scope: str = Field(min_length=1, max_length=4000)
    certificate_manifest: dict | None = None
    remark: str | None = Field(default=None, max_length=2000)


class QualificationDecision(SchemaBase):
    decision_notes: str = Field(min_length=1, max_length=4000)
    valid_days: int = Field(default=365, ge=30, le=1825)
    qualification_level: str = Field(default='STANDARD', min_length=1, max_length=30)


class RejectQualification(SchemaBase):
    decision_notes: str = Field(min_length=1, max_length=4000)


class QualificationApplicationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    application_no: str
    supplier_id: int
    requested_scope: str
    status: SupplierQualificationStatus
    qualification_level: str | None
    submitted_at: datetime | None
    decided_at: datetime | None
    decision_notes: str | None
    approved_at: datetime | None
    valid_until: datetime | None
    next_review_at: datetime | None
    certificate_manifest: dict | None
    remark: str | None
    created_time: datetime


class CreateQualificationAudit(SchemaBase):
    audit_type: SupplierAuditType = SupplierAuditType.INITIAL
    planned_at: datetime
    remark: str | None = Field(default=None, max_length=2000)


class CompleteQualificationAudit(SchemaBase):
    score: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    result: SupplierAuditResult
    findings: str = Field(min_length=1, max_length=8000)
    corrective_due_at: datetime | None = None
    evidence_manifest: dict | None = None


class QualificationAuditDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    audit_no: str
    application_id: int
    supplier_id: int
    audit_type: SupplierAuditType
    planned_at: datetime
    status: SupplierAuditStatus
    conducted_at: datetime | None
    score: Decimal | None
    result: SupplierAuditResult | None
    findings: str | None
    corrective_due_at: datetime | None
    evidence_manifest: dict | None
    remark: str | None


class CreateSampleApproval(SchemaBase):
    material_id: int = Field(ge=1)
    submitted_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    inspection_id: int | None = Field(default=None, ge=1)
    evidence_manifest: dict | None = None


class DecideSampleApproval(SchemaBase):
    approved: bool
    decision_notes: str = Field(min_length=1, max_length=4000)
    inspection_id: int | None = Field(default=None, ge=1)


class SampleApprovalDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sample_no: str
    application_id: int
    supplier_id: int
    material_id: int
    round_no: int
    submitted_quantity: Decimal
    status: SupplierSampleStatus
    inspection_id: int | None
    submitted_at: datetime | None
    decided_at: datetime | None
    decision_notes: str | None
    evidence_manifest: dict | None


class CreatePpapSubmission(SchemaBase):
    material_id: int = Field(ge=1)
    level: int = Field(default=3, ge=1, le=5)
    version: str = Field(default='1.0', min_length=1, max_length=40)
    sample_approval_id: int | None = Field(default=None, ge=1)
    document_manifest: dict = Field(min_length=1)


class DecidePpapSubmission(SchemaBase):
    approved: bool
    decision_notes: str = Field(min_length=1, max_length=4000)
    valid_days: int = Field(default=365, ge=30, le=1825)


class PpapSubmissionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ppap_no: str
    application_id: int
    supplier_id: int
    material_id: int
    level: int
    version: str
    status: SupplierPpapStatus
    sample_approval_id: int | None
    document_manifest: dict | None
    submitted_at: datetime | None
    decided_at: datetime | None
    decision_notes: str | None
    approved_at: datetime | None
    expires_at: datetime | None


class ApprovedMaterialDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int
    material_id: int
    supplier_material_id: int
    qualification_id: int
    ppap_id: int
    status: SupplierAvlStatus
    approved_at: datetime | None
    valid_from: datetime | None
    valid_until: datetime | None
    last_review_at: datetime | None
    next_review_at: datetime | None
    restrictions: str | None


class CreatePeriodicReview(SchemaBase):
    planned_at: datetime | None = None


class CompletePeriodicReview(SchemaBase):
    decision: SupplierReviewDecision
    notes: str = Field(min_length=1, max_length=4000)
    next_review_days: int = Field(default=365, ge=30, le=1825)


class PeriodicReviewDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    review_no: str
    supplier_id: int
    avl_id: int
    planned_at: datetime
    status: SupplierReviewStatus
    quality_assessment_id: int | None
    score_snapshot: Decimal | None
    decision: SupplierReviewDecision | None
    reviewed_at: datetime | None
    next_review_at: datetime | None
    notes: str | None


class SupplierLifecycleDashboard(SchemaBase):
    draft_applications: int
    pending_applications: int
    audits_pending: int
    samples_pending: int
    ppaps_pending: int
    active_avl_entries: int
    avl_expiring_soon: int
    reviews_due: int
    suspended_or_removed: int
