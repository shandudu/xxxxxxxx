from backend.common.enums import StrEnum


class EquipmentType(StrEnum):
    PRODUCTION = 'PRODUCTION'
    INSPECTION = 'INSPECTION'
    LOGISTICS = 'LOGISTICS'
    UTILITY = 'UTILITY'
    TOOL = 'TOOL'
    OTHER = 'OTHER'


class EquipmentStatus(StrEnum):
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    DOWN = 'DOWN'
    MAINTENANCE = 'MAINTENANCE'
    OFFLINE = 'OFFLINE'
    DISABLED = 'DISABLED'


class EquipmentCategoryStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'
