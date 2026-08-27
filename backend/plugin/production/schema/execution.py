from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.production.enums import ProductionExecutionStatus


class StartProductionExecution(SchemaBase):
    execution_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=2000)


class RecordMaterialConsumption(SchemaBase):
    consumption_no: str | None = Field(default=None, max_length=100)
    requirement_id: int = Field(ge=1)
    issue_line_id: int | None = Field(default=None, ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=2000)


class CompleteProductionExecution(SchemaBase):
    good_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    scrap_quantity: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_quantity(self):
        if self.good_quantity + self.scrap_quantity <= 0:
            raise ValueError('execution completion quantity must be positive')
        return self


class MaterialConsumptionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    consumption_no: str
    execution_id: int
    requirement_id: int
    issue_line_id: int | None
    material_id: int
    lot_id: int | None
    quantity: Decimal
    consumed_at: datetime
    operator_id: int | None
    remark: str | None


class ProductionExecutionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_no: str
    work_order_id: int
    work_order_operation_id: int
    status: ProductionExecutionStatus
    good_quantity: Decimal
    scrap_quantity: Decimal
    started_at: datetime
    completed_at: datetime | None
    operator_id: int | None
    remark: str | None
    consumptions: list[MaterialConsumptionDetail] = Field(default_factory=list)
