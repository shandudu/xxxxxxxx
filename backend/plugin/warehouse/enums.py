from backend.common.enums import StrEnum


class WarehouseType(StrEnum):
    RAW_MATERIAL = 'RAW_MATERIAL'
    WIP = 'WIP'
    FINISHED_PRODUCT = 'FINISHED_PRODUCT'
    LINE_SIDE = 'LINE_SIDE'
    QUALITY_HOLD = 'QUALITY_HOLD'
    SCRAP = 'SCRAP'
    VIRTUAL = 'VIRTUAL'


class WarehouseStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class AreaType(StrEnum):
    NORMAL = 'NORMAL'
    RECEIVING = 'RECEIVING'
    SHIPPING = 'SHIPPING'
    QUALITY = 'QUALITY'
    QUARANTINE = 'QUARANTINE'
    TEMP = 'TEMP'
    PRODUCTION = 'PRODUCTION'


class AreaStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class LocationType(StrEnum):
    ZONE = 'ZONE'
    AISLE = 'AISLE'
    RACK = 'RACK'
    LEVEL = 'LEVEL'
    BIN = 'BIN'
    FLOOR = 'FLOOR'
    BUFFER = 'BUFFER'
    LINE = 'LINE'
    WORKSTATION = 'WORKSTATION'
    TEMP = 'TEMP'


class LocationStatus(StrEnum):
    AVAILABLE = 'AVAILABLE'
    LOCKED = 'LOCKED'
    DISABLED = 'DISABLED'

