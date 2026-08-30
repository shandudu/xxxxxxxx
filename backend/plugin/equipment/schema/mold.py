from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.equipment.enums import (
    MoldCavityStatus, MoldCostType, MoldMaintenanceStatus, MoldMaintenanceTrigger,
    MoldMaintenanceType, MoldMountStatus, MoldQualityResult, MoldStatus,
)


class CreateMold(SchemaBase):
    mold_code: str = Field(min_length=1, max_length=100)
    mold_name: str = Field(min_length=1, max_length=200)
    tool_equipment_id: int = Field(ge=1)
    product_material_id: int = Field(ge=1)
    mold_type: str = Field(min_length=1, max_length=50)
    cavity_count: int = Field(ge=1, le=512)
    designed_life_shots: int = Field(gt=0)
    maintenance_interval_shots: int = Field(gt=0)
    warning_percent: Decimal = Field(default=Decimal('90'), gt=0, le=100)
    acquisition_cost: Decimal = Field(default=Decimal('0'), ge=0)
    residual_value: Decimal = Field(default=Decimal('0'), ge=0)
    commission_date: date | None = None
    location: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=150)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_cost_and_interval(self):
        if self.residual_value > self.acquisition_cost:
            raise ValueError('residual value cannot exceed acquisition cost')
        if self.maintenance_interval_shots > self.designed_life_shots:
            raise ValueError('maintenance interval cannot exceed designed life')
        return self


class MoldDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mold_code: str
    mold_name: str
    tool_equipment_id: int
    product_material_id: int
    mold_type: str
    cavity_count: int
    designed_life_shots: int
    maintenance_interval_shots: int
    status: MoldStatus
    warning_percent: Decimal
    current_shots: int
    shots_since_maintenance: int
    mounted_equipment_id: int | None
    acquisition_cost: Decimal
    residual_value: Decimal
    commission_date: date | None
    last_maintenance_at: datetime | None
    next_maintenance_shots: int | None
    location: str | None
    manufacturer: str | None
    remark: str | None
    created_time: datetime


class MoldStatusUpdate(SchemaBase):
    status: MoldStatus
    remark: str | None = Field(default=None, max_length=2000)


class CavityStatusUpdate(SchemaBase):
    status: MoldCavityStatus
    remark: str | None = Field(default=None, max_length=2000)


class MoldCavityDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mold_id: int
    cavity_no: str
    status: MoldCavityStatus
    current_shots: int
    inspected_quantity: Decimal
    defect_quantity: Decimal
    last_defect_at: datetime | None
    last_defect_code: str | None
    remark: str | None


class MountMold(SchemaBase):
    equipment_id: int = Field(ge=1)
    work_order_id: int | None = Field(default=None, ge=1)
    mounted_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=2000)


class UnmountMold(SchemaBase):
    remark: str | None = Field(default=None, max_length=2000)


class MoldMountDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mount_no: str
    mold_id: int
    equipment_id: int
    work_order_id: int | None
    mounted_at: datetime
    opening_shots: int
    status: MoldMountStatus
    unmounted_at: datetime | None
    closing_shots: int | None
    produced_quantity: Decimal
    good_quantity: Decimal
    scrap_quantity: Decimal
    remark: str | None


class MoldUsageDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mold_id: int
    mount_id: int
    work_order_id: int
    production_report_id: int
    shot_count: int
    active_cavity_count: int
    good_quantity: Decimal
    scrap_quantity: Decimal
    reported_at: datetime


class CreateMoldMaintenance(SchemaBase):
    maintenance_type: MoldMaintenanceType
    trigger_type: MoldMaintenanceTrigger = MoldMaintenanceTrigger.MANUAL
    description: str = Field(min_length=1, max_length=4000)
    due_at: datetime | None = None
    due_shots: int | None = Field(default=None, ge=0)
    assigned_user_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=2000)


class CompleteMoldMaintenance(SchemaBase):
    findings: str = Field(min_length=1, max_length=4000)
    action_taken: str = Field(min_length=1, max_length=4000)
    labor_cost: Decimal = Field(default=Decimal('0'), ge=0)
    material_cost: Decimal = Field(default=Decimal('0'), ge=0)
    external_cost: Decimal = Field(default=Decimal('0'), ge=0)


class MoldMaintenanceDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    mold_id: int
    maintenance_type: MoldMaintenanceType
    trigger_type: MoldMaintenanceTrigger
    description: str
    status: MoldMaintenanceStatus
    due_at: datetime | None
    due_shots: int | None
    repair_order_id: int | None
    started_at: datetime | None
    completed_at: datetime | None
    findings: str | None
    action_taken: str | None
    labor_cost: Decimal
    material_cost: Decimal
    external_cost: Decimal
    total_cost: Decimal


class CreateCavityQuality(SchemaBase):
    cavity_id: int = Field(ge=1)
    inspected_quantity: Decimal = Field(gt=0)
    defect_quantity: Decimal = Field(ge=0)
    result: MoldQualityResult
    work_order_id: int | None = Field(default=None, ge=1)
    production_report_id: int | None = Field(default=None, ge=1)
    inspection_id: int | None = Field(default=None, ge=1)
    defect_code: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode='after')
    def validate_quantities(self):
        if self.defect_quantity > self.inspected_quantity:
            raise ValueError('defect quantity cannot exceed inspected quantity')
        if self.result == MoldQualityResult.FAIL and self.defect_quantity <= 0:
            raise ValueError('failed cavity quality requires defect quantity')
        return self


class MoldCavityQualityDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mold_id: int
    cavity_id: int
    inspected_quantity: Decimal
    defect_quantity: Decimal
    result: MoldQualityResult
    checked_at: datetime
    work_order_id: int | None
    production_report_id: int | None
    inspection_id: int | None
    defect_code: str | None
    notes: str | None


class MoldCostEntryDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_no: str
    mold_id: int
    cost_type: MoldCostType
    amount: Decimal
    occurred_at: datetime
    source_type: str | None
    source_id: int | None
    description: str | None


class MoldCostAnalysis(SchemaBase):
    mold_id: int
    acquisition_cost: Decimal
    maintenance_cost: Decimal
    repair_cost: Decimal
    modification_cost: Decimal
    total_lifecycle_cost: Decimal
    current_shots: int
    cost_per_shot: Decimal


class MoldDashboard(SchemaBase):
    total_molds: int
    mounted_molds: int
    maintenance_due: int
    life_warning: int
    life_exceeded: int
    blocked_cavities: int
    open_maintenance_orders: int
    total_lifecycle_cost: Decimal
