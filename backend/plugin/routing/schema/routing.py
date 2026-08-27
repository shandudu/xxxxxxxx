from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.routing.enums import (
    OperationStatus,
    OperationType,
    RoutingStatus,
    RoutingType,
    RunTimeUnit,
    WorkCenterStatus,
    WorkCenterType,
)
from backend.utils.timezone import timezone


CODE_PATTERN = r'^[A-Za-z0-9_-]+$'
VERSION_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = normalize_text(value)
    return text or None


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.tz_info)
    return value


class MaterialSummary(SchemaBase):
    id: int
    code: str
    name: str
    specification: str | None = None
    unit: str = ''


class OperationSummary(SchemaBase):
    id: int
    code: str
    name: str
    status: OperationStatus
    operation_type: OperationType


class WorkCenterSummary(SchemaBase):
    id: int
    code: str
    name: str
    status: WorkCenterStatus
    production_enabled: bool


class OperationConfigBase(SchemaBase):
    operation_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    operation_name: str = Field(min_length=1, max_length=150)
    operation_short_name: str | None = Field(None, max_length=100)
    operation_type: OperationType = OperationType.PROCESS
    description: str | None = Field(None, max_length=1000)
    production_enabled: bool = True
    quality_enabled: bool = False
    trace_enabled: bool = True
    remark: str | None = Field(None, max_length=1000)
    sort_no: int = 0

    @field_validator('operation_code', mode='before')
    @classmethod
    def normalize_operation_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('operation_name', mode='before')
    @classmethod
    def normalize_operation_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('operation_short_name', 'description', 'remark', mode='before')
    @classmethod
    def normalize_optional_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class CreateOperationParam(OperationConfigBase):
    pass


class UpdateOperationParam(OperationConfigBase):
    pass


class OperationStatusParam(SchemaBase):
    status: OperationStatus


class OperationListItem(OperationConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OperationStatus
    created_time: datetime
    updated_time: datetime | None = None


class OperationDetail(OperationListItem):
    pass


class OperationOption(OperationSummary):
    operation_short_name: str | None = None
    quality_enabled: bool
    trace_enabled: bool


class WorkCenterConfigBase(SchemaBase):
    work_center_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    work_center_name: str = Field(min_length=1, max_length=150)
    work_center_type: WorkCenterType = WorkCenterType.OTHER
    factory_code: str | None = Field(None, max_length=50)
    workshop_code: str | None = Field(None, max_length=50)
    location_description: str | None = Field(None, max_length=200)
    production_enabled: bool = True
    scheduling_enabled: bool = True
    capacity_value: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=6)
    capacity_unit: str | None = Field(None, max_length=30)
    parallel_capacity: int = Field(default=1, ge=1)
    remark: str | None = Field(None, max_length=1000)
    sort_no: int = 0

    @field_validator('work_center_code', mode='before')
    @classmethod
    def normalize_work_center_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('work_center_name', mode='before')
    @classmethod
    def normalize_work_center_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator(
        'factory_code', 'workshop_code', 'location_description', 'capacity_unit', 'remark', mode='before'
    )
    @classmethod
    def normalize_optional_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class CreateWorkCenterParam(WorkCenterConfigBase):
    pass


class UpdateWorkCenterParam(WorkCenterConfigBase):
    pass


class WorkCenterStatusParam(SchemaBase):
    status: WorkCenterStatus


class WorkCenterDetail(WorkCenterConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: WorkCenterStatus
    created_time: datetime
    updated_time: datetime | None = None


class WorkCenterOption(WorkCenterSummary):
    work_center_type: WorkCenterType
    factory_code: str | None = None
    workshop_code: str | None = None


class RoutingConfigBase(SchemaBase):
    routing_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    routing_name: str = Field(min_length=1, max_length=150)
    product_material_id: int = Field(ge=1)
    routing_version: str = Field(min_length=1, max_length=30, pattern=VERSION_PATTERN)
    routing_type: RoutingType = RoutingType.STANDARD
    base_quantity: Decimal = Field(default=Decimal('1'), gt=0, max_digits=18, decimal_places=6)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = Field(None, max_length=1000)
    remark: str | None = Field(None, max_length=1000)

    @field_validator('routing_code', 'routing_version', mode='before')
    @classmethod
    def normalize_codes(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('routing_name', mode='before')
    @classmethod
    def normalize_routing_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('description', 'remark', mode='before')
    @classmethod
    def normalize_optional_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @field_validator('effective_from', 'effective_to', mode='after')
    @classmethod
    def normalize_effective_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)

    @model_validator(mode='after')
    def validate_effective_range(self) -> 'RoutingConfigBase':
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('effective_to must be greater than or equal to effective_from')
        return self


class CreateRoutingParam(RoutingConfigBase):
    pass


class UpdateRoutingParam(RoutingConfigBase):
    pass


class CopyRoutingParam(SchemaBase):
    new_routing_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    new_version: str = Field(min_length=1, max_length=30, pattern=VERSION_PATTERN)
    new_routing_name: str | None = Field(None, max_length=150)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    description: str | None = Field(None, max_length=1000)
    remark: str | None = Field(None, max_length=1000)

    @field_validator('new_routing_code', 'new_version', mode='before')
    @classmethod
    def normalize_codes(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('new_routing_name', 'description', 'remark', mode='before')
    @classmethod
    def normalize_optional_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @field_validator('effective_from', 'effective_to', mode='after')
    @classmethod
    def normalize_effective_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)

    @model_validator(mode='after')
    def validate_effective_range(self) -> 'CopyRoutingParam':
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('effective_to must be greater than or equal to effective_from')
        return self


class ActivateRoutingParam(SchemaBase):
    set_as_default: bool = False


class RoutingOperationConfigBase(SchemaBase):
    sequence_no: int = Field(ge=1)
    operation_id: int = Field(ge=1)
    work_center_id: int | None = Field(None, ge=1)
    operation_name_override: str | None = Field(None, max_length=150)
    setup_time_min: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=4)
    run_time_value: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    run_time_unit: RunTimeUnit = RunTimeUnit.MIN_PER_BASE_QTY
    queue_time_min: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=4)
    move_time_min: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=4)
    standard_yield_rate: Decimal = Field(default=Decimal('100'), gt=0, le=100, max_digits=8, decimal_places=4)
    reporting_required: bool = True
    quality_required: bool = False
    trace_required: bool = True
    remark: str | None = Field(None, max_length=500)
    sort_no: int = 0

    @field_validator('operation_name_override', 'remark', mode='before')
    @classmethod
    def normalize_optional_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class CreateRoutingOperationParam(RoutingOperationConfigBase):
    pass


class UpdateRoutingOperationParam(RoutingOperationConfigBase):
    pass


class RoutingOperationDetail(SchemaBase):
    id: int
    routing_id: int
    sequence_no: int
    operation_id: int
    work_center_id: int | None = None
    operation_name_override: str | None = None
    operation_name_snapshot: str | None = None
    operation_display_name: str
    setup_time_min: Decimal
    run_time_value: Decimal
    run_time_unit: RunTimeUnit
    queue_time_min: Decimal
    move_time_min: Decimal
    standard_yield_rate: Decimal
    reporting_required: bool
    quality_required: bool
    trace_required: bool
    remark: str | None = None
    sort_no: int
    operation: OperationSummary
    work_center: WorkCenterSummary | None = None
    created_time: datetime
    updated_time: datetime | None = None


class RoutingListItem(SchemaBase):
    id: int
    routing_code: str
    routing_name: str
    product_material_id: int
    routing_version: str
    routing_type: RoutingType
    base_quantity: Decimal
    status: RoutingStatus
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_default: bool
    description: str | None = None
    remark: str | None = None
    product: MaterialSummary
    operation_count: int
    created_time: datetime
    updated_time: datetime | None = None


class RoutingDetail(RoutingListItem):
    operations: list[RoutingOperationDetail] = Field(default_factory=list)


class RoutingOption(SchemaBase):
    id: int
    code: str
    name: str
    version: str
    routing_type: RoutingType
    is_default: bool


class ReorderRoutingOperationItem(SchemaBase):
    routing_operation_id: int = Field(ge=1)
    sequence_no: int = Field(ge=1)


class ReorderRoutingOperationParam(SchemaBase):
    items: list[ReorderRoutingOperationItem] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_unique_items(self) -> 'ReorderRoutingOperationParam':
        ids = [item.routing_operation_id for item in self.items]
        sequences = [item.sequence_no for item in self.items]
        if len(ids) != len(set(ids)) or len(sequences) != len(set(sequences)):
            raise ValueError('routing operation ids and sequence numbers must be unique')
        return self


class RoutingValidationIssue(SchemaBase):
    code: str
    message: str


class RoutingValidationResult(SchemaBase):
    valid: bool
    errors: list[RoutingValidationIssue] = Field(default_factory=list)
    warnings: list[RoutingValidationIssue] = Field(default_factory=list)


class CalculateRoutingTimeParam(SchemaBase):
    production_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class RoutingTimeItem(SchemaBase):
    routing_operation_id: int
    sequence_no: int
    operation_name: str
    setup_time_min: Decimal
    run_time_min: Decimal
    queue_time_min: Decimal
    move_time_min: Decimal
    total_time_min: Decimal


class RoutingTimeCalculation(SchemaBase):
    routing_id: int
    production_quantity: Decimal
    base_quantity: Decimal
    total_time_min: Decimal
    items: list[RoutingTimeItem] = Field(default_factory=list)
