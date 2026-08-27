from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.costing.enums import CostElement, CostPeriodStatus, CostPostingStatus, MarginDimension


class CostPeriodCreate(SchemaBase):
    period_code: str = Field(min_length=4, max_length=20)
    start_date: date
    end_date: date
    labor_rate_per_hour: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    machine_rate_per_hour: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    overhead_rate_per_hour: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    currency: str = Field(default='CNY', min_length=3, max_length=10)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_dates(self) -> 'CostPeriodCreate':
        if self.end_date < self.start_date:
            raise ValueError('end_date must not be before start_date')
        return self


class CostPeriodDetail(CostPeriodCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: CostPeriodStatus
    closed_at: datetime | None = None


class CostElementDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    element: CostElement
    source_type: str
    source_id: int | None = None
    material_id: int | None = None
    description: str
    quantity: Decimal
    unit_rate: Decimal
    amount: Decimal


class WorkOrderCostDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    period_id: int
    work_order_id: int
    work_order_no_snapshot: str
    product_material_id: int
    product_code_snapshot: str
    product_name_snapshot: str
    good_quantity: Decimal
    scrap_quantity: Decimal
    material_cost: Decimal
    labor_cost: Decimal
    machine_cost: Decimal
    overhead_cost: Decimal
    quality_loss_cost: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    status: CostPostingStatus
    calculated_at: datetime | None = None
    posted_at: datetime | None = None
    lines: list[CostElementDetail] = Field(default_factory=list)


class MarginRow(SchemaBase):
    dimension: MarginDimension
    key: str
    name: str
    shipped_quantity: Decimal
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    margin_rate: Decimal
    cost_coverage: Decimal


class MarginDashboard(SchemaBase):
    period_id: int | None = None
    period_code: str | None = None
    dimension: MarginDimension
    rows: list[MarginRow]
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    margin_rate: Decimal


class CostCalculateRequest(SchemaBase):
    period_id: int

