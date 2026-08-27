from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.quality.enums import (
    InspectionTemplateStatus,
    InspectionType,
    InspectionValueType,
    QualityConfigStatus,
)


class CreateQualityInspectionItem(SchemaBase):
    item_code: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    item_name: str = Field(min_length=1, max_length=200)
    value_type: InspectionValueType
    unit_label: str | None = Field(default=None, max_length=30)

    @field_validator('item_code', mode='before')
    @classmethod
    def normalize_code(cls, value):
        return str(value).strip().upper()


class SetQualityConfigStatus(SchemaBase):
    status: QualityConfigStatus


class QualityInspectionItemDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_code: str
    item_name: str
    value_type: InspectionValueType
    unit_label: str | None
    status: QualityConfigStatus


class CreateQualitySamplingPlan(SchemaBase):
    plan_code: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    plan_name: str = Field(min_length=1, max_length=200)
    sample_size: int = Field(gt=0)
    acceptance_number: int = Field(ge=0)

    @field_validator('plan_code', mode='before')
    @classmethod
    def normalize_code(cls, value):
        return str(value).strip().upper()

    @model_validator(mode='after')
    def validate_acceptance(self):
        if self.acceptance_number > self.sample_size:
            raise ValueError('acceptance number cannot exceed sample size')
        return self


class QualitySamplingPlanDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_code: str
    plan_name: str
    sample_size: int
    acceptance_number: int
    status: QualityConfigStatus


class CreateQualityInspectionTemplate(SchemaBase):
    template_code: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    template_name: str = Field(min_length=1, max_length=200)
    material_id: int = Field(ge=1)
    template_version: str = Field(min_length=1, max_length=30)
    inspection_type: InspectionType
    sampling_plan_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('template_code', mode='before')
    @classmethod
    def normalize_code(cls, value):
        return str(value).strip().upper()


class QualityInspectionTemplateDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_code: str
    template_name: str
    material_id: int
    template_version: str
    inspection_type: InspectionType
    sampling_plan_id: int | None
    status: InspectionTemplateStatus
    remark: str | None


class CreateQualityInspectionStandard(SchemaBase):
    line_no: int = Field(gt=0)
    inspection_item_id: int = Field(ge=1)
    lower_limit: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    upper_limit: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    expected_boolean: bool | None = None
    expected_text: str | None = Field(default=None, max_length=200)
    required: bool = True
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_limits(self):
        if self.lower_limit is not None and self.upper_limit is not None and self.lower_limit > self.upper_limit:
            raise ValueError('lower limit cannot exceed upper limit')
        return self


class QualityInspectionStandardDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    line_no: int
    inspection_item_id: int
    lower_limit: Decimal | None
    upper_limit: Decimal | None
    expected_boolean: bool | None
    expected_text: str | None
    required: bool
    remark: str | None


class SubmitQualityResultLine(SchemaBase):
    standard_id: int = Field(ge=1)
    numeric_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    boolean_value: bool | None = None
    text_value: str | None = Field(default=None, max_length=500)
    remark: str | None = Field(default=None, max_length=2000)


class SubmitQualityResults(SchemaBase):
    template_id: int = Field(ge=1)
    results: list[SubmitQualityResultLine] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_unique_standards(self):
        ids = [item.standard_id for item in self.results]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate inspection standard')
        return self


class QualityInspectionResultLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_id: int
    template_id: int
    standard_id: int
    inspection_item_id: int
    line_no_snapshot: int
    item_code_snapshot: str
    item_name_snapshot: str
    value_type_snapshot: InspectionValueType
    is_qualified: bool
    lower_limit_snapshot: Decimal | None
    upper_limit_snapshot: Decimal | None
    expected_boolean_snapshot: bool | None
    expected_text_snapshot: str | None
    numeric_value: Decimal | None
    boolean_value: bool | None
    text_value: str | None
    remark: str | None
