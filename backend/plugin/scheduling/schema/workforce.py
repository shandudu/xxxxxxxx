from datetime import date, datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.scheduling.enums import ConfigStatus, QualificationStatus, RosterStatus


def clean_text(value: Any) -> str:
    return str(value).strip()


def clean_code(value: Any) -> str:
    return clean_text(value).upper()


class JobTypeInput(SchemaBase):
    job_code: str = Field(min_length=1, max_length=50, pattern=r'^[A-Za-z0-9_-]+$')
    job_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: ConfigStatus = ConfigStatus.ACTIVE

    @field_validator('job_code', mode='before')
    @classmethod
    def code(cls, value: Any) -> str:
        return clean_code(value)

    @field_validator('job_name', mode='before')
    @classmethod
    def name(cls, value: Any) -> str:
        return clean_text(value)


class JobTypeDetail(JobTypeInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime


class SkillLevelInput(SchemaBase):
    level_code: str = Field(min_length=1, max_length=50, pattern=r'^[A-Za-z0-9_-]+$')
    level_name: str = Field(min_length=1, max_length=100)
    rank_order: int = Field(ge=1, le=999)
    description: str | None = Field(default=None, max_length=2000)
    status: ConfigStatus = ConfigStatus.ACTIVE

    @field_validator('level_code', mode='before')
    @classmethod
    def code(cls, value: Any) -> str:
        return clean_code(value)


class SkillLevelDetail(SkillLevelInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime


class WorkerSkillInput(SchemaBase):
    user_id: int = Field(ge=1)
    job_type_id: int = Field(ge=1)
    skill_level_id: int = Field(ge=1)
    assessed_on: date
    expires_on: date | None = None
    assessor: str | None = Field(default=None, max_length=100)
    status: QualificationStatus = QualificationStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def dates(self):
        if self.expires_on and self.expires_on < self.assessed_on:
            raise ValueError('expires_on must not be earlier than assessed_on')
        return self


class WorkerSkillDetail(WorkerSkillInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime


class WorkerCertificateInput(SchemaBase):
    user_id: int = Field(ge=1)
    certificate_type: str = Field(min_length=1, max_length=80)
    certificate_name: str = Field(min_length=1, max_length=150)
    certificate_no: str = Field(min_length=1, max_length=100)
    issued_on: date
    valid_from: date
    expires_on: date
    issuer: str | None = Field(default=None, max_length=150)
    evidence_url: str | None = Field(default=None, max_length=500)
    status: QualificationStatus = QualificationStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('certificate_type', 'certificate_no', mode='before')
    @classmethod
    def normalize_codes(cls, value: Any) -> str:
        return clean_code(value)

    @model_validator(mode='after')
    def dates(self):
        if self.valid_from < self.issued_on or self.expires_on < self.valid_from:
            raise ValueError('certificate dates are invalid')
        return self


class WorkerCertificateDetail(WorkerCertificateInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime
    validity_state: str = 'VALID'


class PositionRuleInput(SchemaBase):
    rule_code: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    rule_name: str = Field(min_length=1, max_length=150)
    job_type_id: int = Field(ge=1)
    minimum_skill_level_id: int = Field(ge=1)
    operation_id: int | None = Field(default=None, ge=1)
    work_center_id: int | None = Field(default=None, ge=1)
    required_certificate_type: str | None = Field(default=None, max_length=80)
    require_authorization: bool = True
    require_roster: bool = True
    status: ConfigStatus = ConfigStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('rule_code', mode='before')
    @classmethod
    def code(cls, value: Any) -> str:
        return clean_code(value)

    @field_validator('required_certificate_type', mode='before')
    @classmethod
    def certificate_type(cls, value: Any) -> str | None:
        return clean_code(value) if value else None

    @model_validator(mode='after')
    def scope(self):
        if not self.operation_id and not self.work_center_id:
            raise ValueError('operation_id or work_center_id is required')
        return self


class PositionRuleDetail(PositionRuleInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime


class WorkerAuthorizationInput(SchemaBase):
    user_id: int = Field(ge=1)
    job_type_id: int = Field(ge=1)
    work_center_id: int = Field(ge=1)
    operation_id: int | None = Field(default=None, ge=1)
    effective_from: date
    effective_to: date | None = None
    status: QualificationStatus = QualificationStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def dates(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError('effective_to must not be earlier than effective_from')
        return self


class WorkerAuthorizationDetail(WorkerAuthorizationInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    approved_by: int | None = None
    created_time: datetime


class WorkerRosterInput(SchemaBase):
    user_id: int = Field(ge=1)
    work_date: date
    shift_id: int = Field(ge=1)
    work_center_id: int = Field(ge=1)
    job_type_id: int = Field(ge=1)
    status: RosterStatus = RosterStatus.CONFIRMED
    remark: str | None = Field(default=None, max_length=2000)


class WorkerRosterDetail(WorkerRosterInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime


class AccessCheckInput(SchemaBase):
    user_id: int = Field(ge=1)
    operation_id: int = Field(ge=1)
    work_center_id: int | None = Field(default=None, ge=1)


class AccessCheckResult(SchemaBase):
    allowed: bool
    enforcement_enabled: bool
    matched_rule_id: int | None = None
    reasons: list[str] = Field(default_factory=list)


class WorkforceDashboard(SchemaBase):
    active_job_types: int
    active_skill_levels: int
    qualified_workers: int
    certificates_expiring_30_days: int
    expired_certificates: int
    active_authorizations: int
    confirmed_today_rosters: int
    active_rules: int
