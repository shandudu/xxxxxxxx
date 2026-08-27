from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.warehouse.enums import (
    AreaStatus,
    AreaType,
    LocationStatus,
    LocationType,
    WarehouseStatus,
    WarehouseType,
)


CODE_PATTERN = r'^[A-Za-z0-9_-]+$'


def normalize_code(value: str) -> str:
    return value.strip().upper()


class WarehouseConfigBase(SchemaBase):
    warehouse_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    warehouse_name: str = Field(min_length=1, max_length=100)
    warehouse_type: WarehouseType
    factory_code: str | None = Field(None, max_length=50)
    status: WarehouseStatus = WarehouseStatus.ACTIVE
    allow_inbound: bool = True
    allow_outbound: bool = True
    remark: str | None = Field(None, max_length=500)
    sort_no: int = 0

    @field_validator('warehouse_code', mode='before')
    @classmethod
    def normalize_warehouse_code(cls, value: Any) -> str:
        return normalize_code(str(value))


class CreateWarehouseConfig(WarehouseConfigBase):
    pass


class UpdateWarehouseConfig(WarehouseConfigBase):
    pass


class WarehouseDetail(WarehouseConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class AreaConfigBase(SchemaBase):
    area_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    area_name: str = Field(min_length=1, max_length=100)
    warehouse_id: int
    area_type: AreaType | None = None
    status: AreaStatus = AreaStatus.ACTIVE
    remark: str | None = Field(None, max_length=500)
    sort_no: int = 0

    @field_validator('area_code', mode='before')
    @classmethod
    def normalize_area_code(cls, value: Any) -> str:
        return normalize_code(str(value))


class CreateAreaConfig(AreaConfigBase):
    pass


class UpdateAreaConfig(AreaConfigBase):
    pass


class AreaDetail(AreaConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class LocationConfigBase(SchemaBase):
    warehouse_id: int
    area_id: int
    parent_id: int | None = None
    location_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    location_name: str = Field(min_length=1, max_length=100)
    location_type: LocationType
    location_level: int = Field(default=1, ge=1)
    status: LocationStatus = LocationStatus.AVAILABLE
    storage_enabled: bool = False
    capacity_value: Decimal | None = Field(None, ge=0)
    capacity_unit: str | None = Field(None, max_length=20)
    mixed_material_allowed: bool = False
    mixed_lot_allowed: bool = False
    remark: str | None = Field(None, max_length=500)
    sort_no: int = 0

    @field_validator('location_code', mode='before')
    @classmethod
    def normalize_location_code(cls, value: Any) -> str:
        return normalize_code(str(value))


class CreateLocationConfig(LocationConfigBase):
    pass


class UpdateLocationConfig(LocationConfigBase):
    pass


class LocationDetail(LocationConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_time: datetime
    updated_time: datetime | None = None


class LocationStatusConfig(SchemaBase):
    status: LocationStatus


class LocationMoveConfig(SchemaBase):
    target_parent_id: int | None = None


class TreeNode(SchemaBase):
    id: int
    node_type: str
    code: str
    name: str
    status: str
    storage_enabled: bool = False
    children: list['TreeNode'] = Field(default_factory=list)


class WarehouseTree(SchemaBase):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    children: list[TreeNode] = Field(default_factory=list)


class LocationRangeConfig(SchemaBase):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    digits: int = Field(default=2, ge=1, le=8)

    @field_validator('end')
    @classmethod
    def validate_end(cls, value: int, info) -> int:
        start = info.data.get('start')
        if start is not None and value < start:
            raise ValueError('end must be greater than or equal to start')
        return value


class LocationGenerateConfig(SchemaBase):
    warehouse_id: int
    area_id: int
    parent_id: int | None = None
    area_prefix: str = Field(min_length=1, max_length=20, pattern=CODE_PATTERN)
    rack: LocationRangeConfig
    level: LocationRangeConfig
    bin: LocationRangeConfig
    pattern: str = Field(default='{AREA}{RACK}-{LEVEL}-{BIN}', min_length=1, max_length=100)
    location_type: LocationType = LocationType.BIN
    location_name_template: str | None = Field(default=None, max_length=100)

    @field_validator('area_prefix', mode='before')
    @classmethod
    def normalize_area_prefix(cls, value: Any) -> str:
        return normalize_code(str(value))


class LocationGeneratePreview(SchemaBase):
    count: int
    examples: list[str]
    conflicts: list[str]

