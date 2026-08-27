from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.trace.enums import (
    LotSourceType,
    LotStatus,
    LotType,
    QualityStatus,
    SequenceResetType,
    SerialStatus,
    TraceObjectType,
    TraceRelationType,
    TraceRuleStatus,
    TraceRuleType,
)


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def _trim(value: Any) -> str:
    return str(value).strip()


class TraceCodeRuleBase(SchemaBase):
    rule_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    rule_name: str = Field(min_length=1, max_length=100)
    rule_type: TraceRuleType
    pattern: str = Field(min_length=1, max_length=200)
    sequence_length: int = Field(default=4, ge=1, le=20)
    sequence_reset_type: SequenceResetType = SequenceResetType.DAILY
    prefix: str | None = Field(default=None, max_length=50)
    status: TraceRuleStatus = TraceRuleStatus.ACTIVE
    example: str | None = Field(default=None, max_length=200)
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('rule_code', mode='before')
    @classmethod
    def normalize_rule_code(cls, value: Any) -> str:
        return _trim(value).upper()

    @field_validator('rule_name', 'pattern', mode='before')
    @classmethod
    def normalize_required_text(cls, value: Any) -> str:
        return _trim(value)

    @field_validator('prefix', 'example', 'remark', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim(value) or None


class CreateTraceCodeRuleParam(TraceCodeRuleBase):
    pass


class UpdateTraceCodeRuleParam(TraceCodeRuleBase):
    pass


class TraceCodeRuleDetail(TraceCodeRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class TraceCodePreviewParam(SchemaBase):
    pattern: str = Field(min_length=1, max_length=200)
    material_id: int | None = Field(default=None, ge=1)
    sequence_length: int = Field(default=4, ge=1, le=20)
    prefix: str | None = Field(default=None, max_length=50)

    @field_validator('pattern', mode='before')
    @classmethod
    def normalize_pattern(cls, value: Any) -> str:
        return _trim(value)


class MaterialTraceRuleParam(SchemaBase):
    lot_rule_id: int | None = Field(default=None, ge=1)
    serial_rule_id: int | None = Field(default=None, ge=1)


class MaterialTraceRuleDetail(MaterialTraceRuleParam):
    material_id: int
    id: int | None = None
    created_time: datetime | None = None
    updated_time: datetime | None = None


class CreateMaterialLotParam(SchemaBase):
    material_id: int = Field(ge=1)
    lot_no: str | None = Field(default=None, max_length=100)
    generate_by_rule: bool = False
    lot_type: LotType = LotType.INTERNAL
    source_type: LotSourceType = LotSourceType.MANUAL
    source_ref_id: int | None = Field(default=None, ge=1)
    source_ref_no: str | None = Field(default=None, max_length=100)
    production_date: datetime | None = None
    expiry_date: datetime | None = None
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    unit_id: int | None = Field(default=None, ge=1)
    status: LotStatus = LotStatus.ACTIVE
    quality_status: QualityStatus = QualityStatus.UNINSPECTED
    supplier_lot_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('lot_no', 'source_ref_no', 'supplier_lot_no', 'remark', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim(value) or None

    @model_validator(mode='after')
    def validate_code_source(self):
        if not self.generate_by_rule and not self.lot_no:
            raise ValueError('lot_no is required when generate_by_rule is false')
        return self


class LotStatusParam(SchemaBase):
    status: LotStatus


class LotListItem(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_no: str
    material_id: int
    material_code: str | None = None
    material_name: str | None = None
    lot_type: LotType
    quantity: Decimal | None = None
    unit_id: int | None = None
    unit_code: str | None = None
    status: LotStatus
    quality_status: QualityStatus
    production_date: datetime | None = None
    expiry_date: datetime | None = None
    created_time: datetime
    updated_time: datetime | None = None


class LotDetail(LotListItem):
    source_type: LotSourceType | None = None
    source_ref_id: int | None = None
    source_ref_no: str | None = None
    parent_lot_id: int | None = None
    supplier_lot_no: str | None = None
    remark: str | None = None


class LotSplitChildParam(SchemaBase):
    lot_no: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)

    @field_validator('lot_no', mode='before')
    @classmethod
    def normalize_lot_no(cls, value: Any) -> str:
        return _trim(value)


class LotSplitParam(SchemaBase):
    children: list[LotSplitChildParam] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def validate_unique_lot_numbers(self):
        lot_numbers = [item.lot_no for item in self.children]
        if len(lot_numbers) != len(set(lot_numbers)):
            raise ValueError('child lot numbers must be unique')
        return self


class LotMergeTargetParam(SchemaBase):
    material_id: int = Field(ge=1)
    lot_no: str = Field(min_length=1, max_length=100)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    unit_id: int | None = Field(default=None, ge=1)
    lot_type: LotType = LotType.INTERNAL
    production_date: datetime | None = None
    expiry_date: datetime | None = None
    quality_status: QualityStatus = QualityStatus.UNINSPECTED
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('lot_no', 'remark', mode='before')
    @classmethod
    def normalize_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim(value) or None


class LotMergeParam(SchemaBase):
    source_lot_ids: list[int] = Field(min_length=2, max_length=1000)
    target_lot: LotMergeTargetParam

    @field_validator('source_lot_ids')
    @classmethod
    def validate_unique_source_lots(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError('source lot IDs must be unique')
        return value


class GenerateMaterialSerialParam(SchemaBase):
    material_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    quantity: int = Field(ge=1, le=10_000)
    production_date: datetime | None = None
    source_type: LotSourceType = LotSourceType.MANUAL
    source_ref_id: int | None = Field(default=None, ge=1)
    source_ref_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator('source_ref_no', 'remark', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim(value) or None


class SerialStatusParam(SchemaBase):
    status: SerialStatus


class MaterialSerialListItem(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_no: str
    material_id: int
    material_code: str | None = None
    material_name: str | None = None
    lot_id: int | None = None
    lot_no: str | None = None
    status: SerialStatus
    quality_status: QualityStatus
    production_date: datetime | None = None
    created_time: datetime
    updated_time: datetime | None = None


class MaterialSerialDetail(MaterialSerialListItem):
    source_type: LotSourceType | None = None
    source_ref_id: int | None = None
    source_ref_no: str | None = None
    remark: str | None = None


class MaterialSerialGenerateResult(SchemaBase):
    count: int
    serials: list[str]


class CreateTraceRelationParam(SchemaBase):
    source_type: TraceObjectType
    source_id: int = Field(ge=1)
    target_type: TraceObjectType
    target_id: int = Field(ge=1)
    relation_type: TraceRelationType
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    unit_id: int | None = Field(default=None, ge=1)
    operation_ref_id: int | None = Field(default=None, ge=1)
    business_ref_type: str | None = Field(default=None, max_length=30)
    business_ref_id: int | None = Field(default=None, ge=1)
    business_ref_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator('business_ref_type', 'business_ref_no', 'remark', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim(value) or None


class TraceRelationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: TraceObjectType
    source_id: int
    source_code: str
    target_type: TraceObjectType
    target_id: int
    target_code: str
    relation_type: TraceRelationType
    quantity: Decimal | None = None
    unit_id: int | None = None
    operation_ref_id: int | None = None
    business_ref_type: str | None = None
    business_ref_id: int | None = None
    business_ref_no: str | None = None
    remark: str | None = None
    created_time: datetime


class TraceNode(SchemaBase):
    object_type: TraceObjectType
    object_id: int
    code: str
    material_id: int
    material_code: str | None = None
    material_name: str | None = None
    relation_type: TraceRelationType | None = None
    quantity: Decimal | None = None
    unit_id: int | None = None
    children: list['TraceNode'] = Field(default_factory=list)

