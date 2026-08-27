from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.equipment.enums import EquipmentCategoryStatus, EquipmentStatus, EquipmentType


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


class CategoryConfigBase(SchemaBase):
    category_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    category_name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = Field(None, ge=1)
    status: EquipmentCategoryStatus = EquipmentCategoryStatus.ACTIVE
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

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_remark(cls, value: Any) -> Any:
        if value is None:
            return value
        return normalize_text(value) or None


class CreateEquipmentCategoryParam(CategoryConfigBase):
    pass


class UpdateEquipmentCategoryParam(CategoryConfigBase):
    pass


class EquipmentCategoryDetail(CategoryConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class EquipmentCategoryTreeNode(SchemaBase):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    status: EquipmentCategoryStatus
    sort_no: int
    remark: str | None = None
    children: list['EquipmentCategoryTreeNode'] = Field(default_factory=list)


class EquipmentConfigBase(SchemaBase):
    equipment_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    equipment_name: str = Field(min_length=1, max_length=150)
    category_id: int = Field(ge=1)
    equipment_type: EquipmentType
    model: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=150)
    serial_number: str | None = Field(None, max_length=100)
    factory_code: str | None = Field(None, max_length=50)
    area_code: str | None = Field(None, max_length=50)
    installation_location: str | None = Field(None, max_length=200)
    enabled: bool = True
    production_enabled: bool = True
    data_collection_enabled: bool = False
    maintenance_enabled: bool = True
    commission_date: date | None = None
    service_date: date | None = None
    rated_capacity: Decimal | None = Field(None, max_digits=18, decimal_places=6, ge=0)
    capacity_unit: str | None = Field(None, max_length=30)
    remark: str | None = Field(None, max_length=1000)

    @field_validator('equipment_code', mode='before')
    @classmethod
    def normalize_equipment_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('equipment_name', mode='before')
    @classmethod
    def normalize_equipment_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator(
        'model',
        'manufacturer',
        'serial_number',
        'factory_code',
        'area_code',
        'installation_location',
        'capacity_unit',
        'remark',
        mode='before',
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if value is None:
            return value
        return normalize_text(value) or None


class CreateEquipmentParam(EquipmentConfigBase):
    pass


class UpdateEquipmentParam(EquipmentConfigBase):
    pass


class EquipmentEnabledParam(SchemaBase):
    enabled: bool


class EquipmentStatusParam(SchemaBase):
    status: EquipmentStatus


class EquipmentListItem(SchemaBase):
    id: int
    equipment_code: str
    equipment_name: str
    category_id: int
    category_name: str | None = None
    equipment_type: EquipmentType
    model: str | None = None
    manufacturer: str | None = None
    serial_number: str | None = None
    factory_code: str | None = None
    area_code: str | None = None
    installation_location: str | None = None
    status: EquipmentStatus
    enabled: bool
    production_enabled: bool
    data_collection_enabled: bool
    maintenance_enabled: bool
    commission_date: date | None = None
    service_date: date | None = None
    rated_capacity: Decimal | None = None
    capacity_unit: str | None = None
    remark: str | None = None
    created_time: datetime
    updated_time: datetime | None = None


class EquipmentDetail(EquipmentListItem):
    created_by: int | None = None
    updated_by: int | None = None


class EquipmentOption(SchemaBase):
    id: int
    code: str
    name: str
    type: EquipmentType
    status: EquipmentStatus
