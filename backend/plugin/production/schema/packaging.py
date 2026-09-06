from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.production.packaging_enums import (
    HandlingUnitStatus, HandlingUnitType, PackagingInspectionResult, PackagingScanType,
    PackagingSpecStatus, PackagingTaskStatus, WeightCheckResult,
)


class CreatePackagingSpecification(SchemaBase):
    spec_code: str = Field(min_length=1, max_length=80)
    spec_name: str = Field(min_length=1, max_length=150)
    material_id: int = Field(ge=1)
    units_per_carton: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    version: str = Field(default='V1', min_length=1, max_length=30)
    cartons_per_pallet: int | None = Field(default=None, ge=1)
    allow_mixed_lot: bool = False
    allow_partial_carton: bool = False
    require_quality_release: bool = True
    require_weight_check: bool = False
    target_gross_weight: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    weight_tolerance: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    label_template_code: str | None = Field(default=None, max_length=80)
    effective_from: date | None = None
    effective_to: date | None = None
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_weight_and_dates(self) -> 'CreatePackagingSpecification':
        if self.require_weight_check and (self.target_gross_weight is None or self.weight_tolerance is None):
            raise ValueError('WEIGHT_TARGET_AND_TOLERANCE_REQUIRED')
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError('INVALID_EFFECTIVE_DATE_RANGE')
        return self


class PackagingSpecificationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spec_code: str
    spec_name: str
    material_id: int
    units_per_carton: Decimal
    version: str
    cartons_per_pallet: int | None
    allow_mixed_lot: bool
    allow_partial_carton: bool
    require_quality_release: bool
    require_weight_check: bool
    target_gross_weight: Decimal | None
    weight_tolerance: Decimal | None
    label_template_code: str | None
    effective_from: date | None
    effective_to: date | None
    status: PackagingSpecStatus
    remark: str | None
    created_time: datetime


class SetPackagingSpecificationStatus(SchemaBase):
    status: PackagingSpecStatus


class CreatePackagingTask(SchemaBase):
    production_report_id: int = Field(ge=1)
    specification_id: int = Field(ge=1)
    planned_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    task_no: str | None = Field(default=None, max_length=100)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=180)
    remark: str | None = Field(default=None, max_length=2000)


class CreateHandlingUnit(SchemaBase):
    hu_type: HandlingUnitType = HandlingUnitType.CARTON
    hu_code: str | None = Field(default=None, max_length=120)
    parent_hu_id: int | None = Field(default=None, ge=1)
    capacity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=2000)


class ScanPackagingItem(SchemaBase):
    code: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=180)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)


class RecordPackagingWeight(SchemaBase):
    gross_weight: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    tare_weight: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    idempotency_key: str = Field(min_length=8, max_length=180)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_net_weight(self) -> 'RecordPackagingWeight':
        if self.gross_weight <= self.tare_weight:
            raise ValueError('GROSS_WEIGHT_MUST_EXCEED_TARE_WEIGHT')
        return self


class SealHandlingUnit(SchemaBase):
    remark: str | None = Field(default=None, max_length=2000)


class ReopenHandlingUnit(SchemaBase):
    reason: str = Field(min_length=3, max_length=500)


class InspectHandlingUnit(SchemaBase):
    result: PackagingInspectionResult
    idempotency_key: str = Field(min_length=8, max_length=180)
    appearance_passed: bool = True
    quantity_passed: bool = True
    label_passed: bool = True
    notes: str | None = Field(default=None, max_length=2000)


class PrintPackagingLabel(SchemaBase):
    idempotency_key: str = Field(min_length=8, max_length=180)
    template_code: str | None = Field(default=None, max_length=80)
    printer_name: str | None = Field(default=None, max_length=120)
    copies: int = Field(default=1, ge=1, le=20)
    reason: str | None = Field(default=None, max_length=500)


class PackagingContentDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hu_id: int
    material_id: int
    production_report_id: int
    scan_type: PackagingScanType
    scanned_code: str
    quantity: Decimal
    lot_id: int | None
    serial_id: int | None
    created_time: datetime


class PackagingHandlingUnitDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hu_code: str
    task_id: int
    hu_type: HandlingUnitType
    parent_hu_id: int | None
    capacity: Decimal
    quantity: Decimal
    tare_weight: Decimal | None
    gross_weight: Decimal | None
    net_weight: Decimal | None
    weight_result: WeightCheckResult | None
    status: HandlingUnitStatus
    sealed_at: datetime | None
    released_at: datetime | None
    stored_at: datetime | None
    version: int
    remark: str | None
    created_time: datetime
    contents: list[PackagingContentDetail] = Field(default_factory=list)


class PackagingTaskDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_no: str
    production_report_id: int
    work_order_id: int
    material_id: int
    lot_id: int | None
    specification_id: int
    planned_quantity: Decimal
    packed_quantity: Decimal
    stock_transaction_id: int | None
    status: PackagingTaskStatus
    started_at: datetime | None
    packed_at: datetime | None
    released_at: datetime | None
    remark: str | None
    created_time: datetime
    handling_units: list[PackagingHandlingUnitDetail] = Field(default_factory=list)


class PackagingWeightRecordDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hu_id: int
    gross_weight: Decimal
    tare_weight: Decimal
    net_weight: Decimal
    result: WeightCheckResult
    created_time: datetime


class PackagingInspectionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hu_id: int
    result: PackagingInspectionResult
    appearance_passed: bool
    quantity_passed: bool
    label_passed: bool
    notes: str | None
    created_time: datetime


class PackagingLabelPrintDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hu_id: int
    template_code: str
    copies: int
    printer_name: str | None
    reason: str | None
    created_time: datetime


class PackagingDashboard(SchemaBase):
    draft_tasks: int
    active_tasks: int
    packed_tasks: int
    released_tasks: int
    open_handling_units: int
    held_handling_units: int
    planned_quantity: Decimal
    packed_quantity: Decimal
