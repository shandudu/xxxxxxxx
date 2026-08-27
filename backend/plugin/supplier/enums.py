from enum import StrEnum


class SupplierCategoryStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class SupplierStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class SupplierType(StrEnum):
    MATERIAL = 'MATERIAL'
    EQUIPMENT = 'EQUIPMENT'
    SPARE_PART = 'SPARE_PART'
    SERVICE = 'SERVICE'
    LOGISTICS = 'LOGISTICS'
    OTHER = 'OTHER'


class CompanyType(StrEnum):
    COMPANY = 'COMPANY'
    INDIVIDUAL = 'INDIVIDUAL'
    ORGANIZATION = 'ORGANIZATION'


class CooperationStatus(StrEnum):
    NORMAL = 'NORMAL'
    SUSPENDED = 'SUSPENDED'
    BLACKLISTED = 'BLACKLISTED'


class SupplierQualityStatus(StrEnum):
    QUALIFIED = 'QUALIFIED'
    CONDITIONAL = 'CONDITIONAL'
    UNQUALIFIED = 'UNQUALIFIED'
    PENDING = 'PENDING'


class ContactType(StrEnum):
    BUSINESS = 'BUSINESS'
    PURCHASE = 'PURCHASE'
    QUALITY = 'QUALITY'
    TECHNICAL = 'TECHNICAL'
    FINANCE = 'FINANCE'
    AFTER_SALES = 'AFTER_SALES'
    OTHER = 'OTHER'


class ContactStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class SupplierMaterialStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    SUSPENDED = 'SUSPENDED'
    DISABLED = 'DISABLED'
