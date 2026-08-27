from backend.common.enums import StrEnum


class MaterialType(StrEnum):
    RAW_MATERIAL = 'RAW_MATERIAL'
    SEMI_FINISHED = 'SEMI_FINISHED'
    FINISHED_PRODUCT = 'FINISHED_PRODUCT'
    AUXILIARY = 'AUXILIARY'
    PACKAGING = 'PACKAGING'
    SPARE_PART = 'SPARE_PART'
    CONSUMABLE = 'CONSUMABLE'


class MaterialStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class CategoryStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class UnitStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'
