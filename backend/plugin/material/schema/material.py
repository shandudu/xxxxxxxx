from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.material.enums import CategoryStatus, MaterialStatus, MaterialType, UnitStatus


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


class CategoryConfigBase(SchemaBase):
    category_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    category_name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = Field(None, ge=1)
    status: CategoryStatus = CategoryStatus.ACTIVE
    sort_no: int = 0
    remark: str | None = Field(None, max_length=500)

    @field_validator('category_code', mode='before')
    @classmethod
    def normalize_category_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('category_name', mode='before')
    @classmethod
    def normalize_category_name(cls, value: Any) -> str:
        return normalize_text(value)


class CreateCategoryParam(CategoryConfigBase):
    pass


class UpdateCategoryParam(CategoryConfigBase):
    pass


class CategoryDetail(CategoryConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class CategoryTreeNode(SchemaBase):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    status: CategoryStatus
    sort_no: int
    remark: str | None = None
    children: list['CategoryTreeNode'] = Field(default_factory=list)


class UnitConfigBase(SchemaBase):
    unit_code: str = Field(min_length=1, max_length=20, pattern=CODE_PATTERN)
    unit_name: str = Field(min_length=1, max_length=50)
    symbol: str | None = Field(None, max_length=20)
    status: UnitStatus = UnitStatus.ACTIVE
    decimal_places: int = Field(0, ge=0, le=6)
    remark: str | None = Field(None, max_length=200)

    @field_validator('unit_code', mode='before')
    @classmethod
    def normalize_unit_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('unit_name', mode='before')
    @classmethod
    def normalize_unit_name(cls, value: Any) -> str:
        return normalize_text(value)


class CreateUnitParam(UnitConfigBase):
    pass


class UpdateUnitParam(UnitConfigBase):
    pass


class UnitDetail(UnitConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class MaterialConfigBase(SchemaBase):
    material_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    material_name: str = Field(min_length=1, max_length=200)
    material_short_name: str | None = Field(None, max_length=100)
    material_type: MaterialType
    category_id: int = Field(ge=1)
    base_unit_id: int = Field(ge=1)
    specification: str | None = Field(None, max_length=200)
    model: str | None = Field(None, max_length=100)
    status: MaterialStatus = MaterialStatus.ACTIVE
    batch_control: bool = False
    serial_control: bool = False
    purchasable: bool = False
    producible: bool = False
    sellable: bool = False
    quality_inspection_required: bool = False
    default_warehouse_id: int | None = Field(None, ge=1)
    shelf_life_days: int | None = Field(None, ge=0)
    remark: str | None = Field(None, max_length=1000)

    @field_validator('material_code', mode='before')
    @classmethod
    def normalize_material_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('material_name', mode='before')
    @classmethod
    def normalize_material_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('material_short_name', 'specification', 'model', 'remark', mode='before')
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if value is None:
            return value
        normalized = str(value).strip()
        return normalized or None


class CreateMaterialParam(MaterialConfigBase):
    pass


class UpdateMaterialParam(MaterialConfigBase):
    pass


class MaterialStatusParam(SchemaBase):
    status: MaterialStatus


class MaterialListItem(SchemaBase):
    id: int
    material_code: str
    material_name: str
    material_short_name: str | None = None
    material_type: MaterialType
    category_id: int
    category_name: str | None = None
    base_unit_id: int
    unit_code: str | None = None
    specification: str | None = None
    model: str | None = None
    status: MaterialStatus
    batch_control: bool
    serial_control: bool
    purchasable: bool
    producible: bool
    sellable: bool
    quality_inspection_required: bool
    default_warehouse_id: int | None = None
    warehouse_name: str | None = None
    shelf_life_days: int | None = None
    remark: str | None = None
    created_time: datetime
    updated_time: datetime | None = None


class MaterialDetail(MaterialListItem):
    pass


class MaterialOption(SchemaBase):
    id: int
    code: str
    name: str
    specification: str | None = None
    unit: str


class WarehouseOption(SchemaBase):
    id: int
    code: str
    name: str
    status: str
