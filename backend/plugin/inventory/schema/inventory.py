from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.inventory.enums import InventoryPolicyStatus, ReplenishmentAlertLevel, ReplenishmentOrderType, ReplenishmentStatus, StockMovementStatus, StockTransactionType


class InventoryBalanceDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    lot_id: int | None
    warehouse_id: int
    location_id: int
    quantity: Decimal
    reserved_quantity: Decimal
    version: int
    created_time: datetime
    updated_time: datetime | None = None

    @property
    def available_quantity(self) -> Decimal:
        return self.quantity - self.reserved_quantity


class StockTransactionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_no: str
    transaction_type: StockTransactionType
    material_id: int
    lot_id: int | None
    warehouse_id: int
    location_id: int
    quantity_delta: Decimal
    balance_after: Decimal
    reference_type: str | None
    reference_id: int | None
    reference_no: str | None
    remark: str | None
    operator_id: int | None
    occurred_at: datetime


class StockMovementLineConfig(SchemaBase):
    material_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    from_warehouse_id: int = Field(ge=1)
    from_location_id: int = Field(ge=1)
    to_warehouse_id: int = Field(ge=1)
    to_location_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_endpoints(self):
        if self.from_location_id == self.to_location_id:
            raise ValueError('source and target location must be different')
        return self


class CreateStockMovement(SchemaBase):
    movement_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)
    lines: list[StockMovementLineConfig] = Field(min_length=1, max_length=500)


class StockMovementLineDetail(StockMovementLineConfig):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_id: int
    line_no: int


class StockMovementDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_no: str
    status: StockMovementStatus
    remark: str | None
    posted_at: datetime | None
    posted_by: int | None
    created_time: datetime
    updated_time: datetime | None = None
    lines: list[StockMovementLineDetail] = Field(default_factory=list)


class StockAdjustmentConfig(SchemaBase):
    idempotency_key: str = Field(min_length=1, max_length=180)
    material_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    quantity_delta: Decimal = Field(max_digits=18, decimal_places=6)
    reference_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_quantity(self):
        if self.quantity_delta == 0:
            raise ValueError('quantity_delta must not be zero')
        return self


class InventoryPolicyUpsert(SchemaBase):
    safety_stock: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    reorder_point: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    max_stock: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    min_order_quantity: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    purchase_lead_days: int = Field(default=7, ge=0, le=3650)
    production_lead_days: int = Field(default=1, ge=0, le=3650)
    review_period_days: int = Field(default=7, ge=0, le=3650)
    status: InventoryPolicyStatus = InventoryPolicyStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=500)


class InventoryPolicyDetail(InventoryPolicyUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int
    created_time: datetime
    updated_time: datetime | None = None


class ReplenishmentSuggestionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    suggestion_no: str
    material_id: int
    policy_id: int
    evaluated_at: datetime
    due_date: date
    material_code_snapshot: str
    material_name_snapshot: str
    unit_code_snapshot: str
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    open_purchase_quantity: Decimal
    open_production_quantity: Decimal
    demand_quantity: Decimal
    projected_available_quantity: Decimal
    safety_stock: Decimal
    reorder_point: Decimal
    suggested_quantity: Decimal
    order_type: ReplenishmentOrderType
    alert_level: ReplenishmentAlertLevel
    status: ReplenishmentStatus
    source_document_type: str | None
    source_document_id: int | None
    source_document_no: str | None
    released_at: datetime | None
    remark: str | None


class GenerateReplenishment(SchemaBase):
    material_ids: list[int] | None = Field(default=None, min_length=1, max_length=1000)


class ReleaseReplenishment(SchemaBase):
    supplier_id: int | None = Field(default=None, ge=1)
    routing_id: int | None = Field(default=None, ge=1)
    currency: str = Field(default='CNY', min_length=3, max_length=10)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=500)


class ReplenishmentDashboard(SchemaBase):
    policy_count: int
    suggestion_count: int
    shortage_count: int
    reorder_count: int
    total_suggested_quantity: Decimal
    total_demand_quantity: Decimal
    purchase_suggestion_count: int
    production_suggestion_count: int
