from backend.common.enums import StrEnum


class BomStatus(StrEnum):
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
