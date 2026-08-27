from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.bom.enums import BomStatus
from backend.utils.timezone import timezone


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.tz_info)
    return value


class BomConfigBase(SchemaBase):
    bom_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    product_material_id: int = Field(ge=1)
    bom_version: str = Field(min_length=1, max_length=30, pattern=CODE_PATTERN)
    base_quantity: Decimal = Field(default=Decimal('1'), gt=0, max_digits=18, decimal_places=6)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    remark: str | None = Field(None, max_length=1000)

    @field_validator('bom_code', 'bom_version', mode='before')
    @classmethod
    def normalize_codes(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @field_validator('effective_from', 'effective_to', mode='after')
    @classmethod
    def normalize_effective_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)

    @model_validator(mode='after')
    def validate_effective_range(self) -> 'BomConfigBase':
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('effective_to must be greater than or equal to effective_from')
        return self


class CreateBomParam(BomConfigBase):
    pass


class UpdateBomParam(BomConfigBase):
    pass


class BomItemConfigBase(SchemaBase):
    line_no: int = Field(ge=1)
    component_material_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_id: int | None = Field(None, ge=1)
    loss_rate: Decimal = Field(default=Decimal('0'), ge=0, max_digits=8, decimal_places=4)
    fixed_loss_qty: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    is_optional: bool = False
    remark: str | None = Field(None, max_length=500)
    sort_no: int = 0

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_item_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class CreateBomItemParam(BomItemConfigBase):
    pass


class UpdateBomItemParam(BomItemConfigBase):
    pass


class CopyBomParam(SchemaBase):
    new_bom_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    new_version: str = Field(min_length=1, max_length=30, pattern=CODE_PATTERN)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    remark: str | None = Field(None, max_length=1000)

    @field_validator('new_bom_code', 'new_version', mode='before')
    @classmethod
    def normalize_copy_codes(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_copy_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @field_validator('effective_from', 'effective_to', mode='after')
    @classmethod
    def normalize_effective_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)

    @model_validator(mode='after')
    def validate_effective_range(self) -> 'CopyBomParam':
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('effective_to must be greater than or equal to effective_from')
        return self


class CalculateBomParam(SchemaBase):
    production_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    production_date: datetime | None = None
    explode: bool = False

    @field_validator('production_date', mode='after')
    @classmethod
    def normalize_production_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value)


class MaterialSummary(SchemaBase):
    id: int
    code: str
    name: str
    specification: str | None = None
    model: str | None = None
    unit: str


class BomItemDetail(BomItemConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bom_id: int
    unit_id: int
    component: MaterialSummary
    created_time: datetime
    updated_time: datetime | None = None


class BomListItem(SchemaBase):
    id: int
    bom_code: str
    bom_version: str
    product_material_id: int
    status: BomStatus
    base_quantity: Decimal
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_default: bool
    remark: str | None = None
    product: MaterialSummary
    created_time: datetime
    updated_time: datetime | None = None


class BomDetail(BomListItem):
    items: list[BomItemDetail] = Field(default_factory=list)


class BomTreeNode(SchemaBase):
    material_id: int
    material_code: str
    material_name: str
    specification: str | None = None
    quantity: Decimal
    unit: str
    line_no: int | None = None
    loss_rate: Decimal | None = None
    fixed_loss_qty: Decimal | None = None
    is_optional: bool = False
    children: list['BomTreeNode'] = Field(default_factory=list)


class BomTree(SchemaBase):
    bom_id: int
    bom_code: str
    bom_version: str
    material_id: int
    material_code: str
    material_name: str
    quantity: Decimal = Decimal('1')
    unit: str
    children: list[BomTreeNode] = Field(default_factory=list)


class BomOption(SchemaBase):
    id: int
    bom_code: str
    bom_version: str
    status: BomStatus
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_default: bool


class MaterialRequirement(SchemaBase):
    material_id: int
    material_code: str
    material_name: str
    standard_required_qty: Decimal
    loss_rate: Decimal
    fixed_loss_qty: Decimal
    planned_required_qty: Decimal
    unit: str
    is_optional: bool = False


class BomValidationResult(SchemaBase):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class BomCompareChange(SchemaBase):
    change_type: str
    component_material_id: int
    component_code: str
    component_name: str
    source_quantity: Decimal | None = None
    target_quantity: Decimal | None = None
    source_loss_rate: Decimal | None = None
    target_loss_rate: Decimal | None = None


class BomCompareResult(SchemaBase):
    source_bom_id: int
    target_bom_id: int
    changes: list[BomCompareChange] = Field(default_factory=list)
