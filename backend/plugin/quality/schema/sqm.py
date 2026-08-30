from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.quality.enums import (
    SupplierCorrectiveActionStatus,
    SupplierCorrectiveVerificationResult,
    SupplierProcurementDecision,
    SupplierQualityGrade,
    SupplierQualityPolicyStatus,
)


class IssueSupplierCorrectiveAction(SchemaBase):
    due_at: datetime | None = None


class RespondSupplierCorrectiveAction(SchemaBase):
    containment_action: str = Field(min_length=1, max_length=4000)
    root_cause: str = Field(min_length=1, max_length=4000)
    corrective_action: str = Field(min_length=1, max_length=4000)
    preventive_action: str = Field(min_length=1, max_length=4000)
    response_evidence: str | None = Field(default=None, max_length=4000)


class VerifySupplierCorrectiveAction(SchemaBase):
    verification_notes: str = Field(min_length=1, max_length=4000)


class SupplierCorrectiveActionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scar_no: str
    supplier_id: int
    ncr_id: int
    inspection_id: int
    supplier_receipt_id: int
    material_id: int
    nonconforming_quantity: Decimal
    defect_description: str
    severity: str
    status: SupplierCorrectiveActionStatus
    due_at: datetime | None
    issued_at: datetime | None
    containment_action: str | None
    root_cause: str | None
    corrective_action: str | None
    preventive_action: str | None
    response_evidence: str | None
    responded_at: datetime | None
    disposition_id: int | None
    reinspection_id: int | None
    verification_result: SupplierCorrectiveVerificationResult | None
    verification_notes: str | None
    verified_at: datetime | None
    closed_at: datetime | None
    created_time: datetime


class SupplierQualityPolicyUpsert(SchemaBase):
    rolling_days: int = Field(default=180, ge=30, le=1095)
    minimum_inspections: int = Field(default=1, ge=1, le=1000)
    excellent_score: Decimal = Field(default=Decimal('95'), ge=0, le=100)
    qualified_score: Decimal = Field(default=Decimal('85'), ge=0, le=100)
    conditional_score: Decimal = Field(default=Decimal('70'), ge=0, le=100)
    quality_weight: Decimal = Field(default=Decimal('70'), ge=0, le=100)
    delivery_weight: Decimal = Field(default=Decimal('30'), ge=0, le=100)
    auto_apply: bool = True
    block_on_open_critical_scar: bool = True
    status: SupplierQualityPolicyStatus = SupplierQualityPolicyStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_thresholds_and_weights(self):
        if not self.conditional_score < self.qualified_score < self.excellent_score:
            raise ValueError('score thresholds must be conditional < qualified < excellent')
        if self.quality_weight + self.delivery_weight != Decimal('100'):
            raise ValueError('quality_weight and delivery_weight must total 100')
        return self


class SupplierQualityPolicyDetail(SupplierQualityPolicyUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int


class SupplierQualityAssessmentDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    assessment_no: str
    supplier_id: int
    policy_id: int
    period_start: datetime
    period_end: datetime
    assessed_at: datetime
    grade: SupplierQualityGrade
    procurement_decision: SupplierProcurementDecision
    overall_score: Decimal
    inspection_count: int
    passed_count: int
    failed_count: int
    inspected_quantity: Decimal
    rejected_quantity: Decimal
    pass_rate: Decimal
    acceptance_rate: Decimal
    scar_count: int
    scar_closed_count: int
    scar_on_time_count: int
    corrective_score: Decimal
    quality_score: Decimal
    delivery_line_count: int
    otif_line_count: int
    delivery_score: Decimal
    critical_scar_open: bool
    applied_at: datetime | None
    applied_notes: str | None


class SupplierQualityDashboard(SchemaBase):
    open_scar_count: int
    overdue_scar_count: int
    retest_pending_count: int
    suspended_supplier_count: int
    conditional_supplier_count: int
    grade_counts: dict[str, int]
