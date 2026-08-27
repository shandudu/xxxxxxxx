from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.planning.enums import (
    MpsDemandType,
    MpsPlanStatus,
    MrpRunStatus,
    PlannedOrderStatus,
    PlannedOrderType,
)


class CreateMpsPlan(SchemaBase):
    plan_no: str | None = Field(default=None, max_length=100)
    plan_name: str = Field(min_length=1, max_length=200)
    horizon_start: date
    horizon_end: date
    remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_horizon(self):
        if self.horizon_end < self.horizon_start:
            raise ValueError('horizon_end must be on or after horizon_start')
        return self


class CreateMpsDemand(SchemaBase):
    material_id: int = Field(ge=1)
    demand_date: date
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    demand_type: MpsDemandType = MpsDemandType.MANUAL
    remark: str | None = Field(default=None, max_length=500)


class ImportSalesOrderDemand(SchemaBase):
    sales_order_ids: list[int] = Field(min_length=1, max_length=500)
    demand_date: date


class MpsDemandDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mps_plan_id: int
    line_no: int
    material_id: int
    unit_id: int
    demand_type: MpsDemandType
    demand_date: date
    quantity: Decimal
    material_code_snapshot: str
    material_name_snapshot: str
    unit_code_snapshot: str
    source_id: int | None
    source_no: str | None
    remark: str | None
    created_time: datetime


class MpsPlanDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_no: str
    plan_name: str
    horizon_start: date
    horizon_end: date
    status: MpsPlanStatus
    remark: str | None
    created_time: datetime
    updated_time: datetime | None
    demands: list[MpsDemandDetail] = Field(default_factory=list)


class CreateMrpRun(SchemaBase):
    mps_plan_id: int = Field(ge=1)
    include_inventory: bool = True
    include_open_purchase: bool = True
    include_open_production: bool = True
    default_purchase_lead_days: int = Field(default=7, ge=0, le=3650)
    default_production_lead_days: int = Field(default=1, ge=0, le=3650)
    max_level: int = Field(default=20, ge=1, le=100)


class MrpRequirementDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mrp_run_id: int
    sequence_no: int
    mps_demand_id: int
    level_no: int
    material_id: int
    parent_material_id: int | None
    bom_id: int | None
    bom_item_id: int | None
    requirement_date: date
    gross_requirement: Decimal
    on_hand_allocated: Decimal
    purchase_supply_allocated: Decimal
    production_supply_allocated: Decimal
    net_requirement: Decimal
    planned_order_quantity: Decimal
    uncovered_quantity: Decimal
    material_code_snapshot: str
    material_name_snapshot: str
    unit_code_snapshot: str
    source_path: str


class PlannedOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    planned_order_no: str
    mrp_run_id: int
    mrp_requirement_id: int
    sequence_no: int
    material_id: int
    order_type: PlannedOrderType
    status: PlannedOrderStatus
    quantity: Decimal
    release_date: date
    due_date: date
    material_code_snapshot: str
    material_name_snapshot: str
    unit_code_snapshot: str
    bom_id: int | None
    source_document_type: str | None
    source_document_id: int | None
    source_document_no: str | None
    firmed_at: datetime | None
    released_at: datetime | None
    remark: str | None


class MrpRunDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    mps_plan_id: int
    status: MrpRunStatus
    include_inventory: bool
    include_open_purchase: bool
    include_open_production: bool
    default_purchase_lead_days: int
    default_production_lead_days: int
    max_level: int
    requirement_count: int
    planned_order_count: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    promise_refresh_at: datetime | None
    promise_assessment_count: int
    created_time: datetime
    requirements: list[MrpRequirementDetail] = Field(default_factory=list)
    planned_orders: list[PlannedOrderDetail] = Field(default_factory=list)


class ReleasePlannedOrder(SchemaBase):
    supplier_id: int | None = Field(default=None, ge=1)
    routing_id: int | None = Field(default=None, ge=1)
    currency: str = Field(default='CNY', min_length=3, max_length=10)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)
