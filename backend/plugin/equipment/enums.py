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


class MoldStatus(StrEnum):
    AVAILABLE = 'AVAILABLE'
    MOUNTED = 'MOUNTED'
    MAINTENANCE = 'MAINTENANCE'
    REPAIR = 'REPAIR'
    SUSPENDED = 'SUSPENDED'
    RETIRED = 'RETIRED'
    SCRAPPED = 'SCRAPPED'


class MoldCavityStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    BLOCKED = 'BLOCKED'
    REPAIR = 'REPAIR'
    DISABLED = 'DISABLED'


class MoldMountStatus(StrEnum):
    MOUNTED = 'MOUNTED'
    UNMOUNTED = 'UNMOUNTED'


class MoldMaintenanceType(StrEnum):
    PREVENTIVE = 'PREVENTIVE'
    REPAIR = 'REPAIR'


class MoldMaintenanceStatus(StrEnum):
    PLANNED = 'PLANNED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class MoldMaintenanceTrigger(StrEnum):
    SHOT_COUNT = 'SHOT_COUNT'
    TIME = 'TIME'
    FAULT = 'FAULT'
    QUALITY = 'QUALITY'
    MANUAL = 'MANUAL'


class MoldQualityResult(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'


class MoldCostType(StrEnum):
    ACQUISITION = 'ACQUISITION'
    MAINTENANCE = 'MAINTENANCE'
    REPAIR = 'REPAIR'
    MODIFICATION = 'MODIFICATION'
    SCRAP = 'SCRAP'
