from enum import StrEnum


class CustomerCategoryStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class CustomerStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class CooperationStatus(StrEnum):
    NORMAL = 'NORMAL'
    SUSPENDED = 'SUSPENDED'
    BLOCKED = 'BLOCKED'


class CustomerType(StrEnum):
    ENTERPRISE = 'ENTERPRISE'
    DISTRIBUTOR = 'DISTRIBUTOR'
    END_CUSTOMER = 'END_CUSTOMER'
    INTERNAL = 'INTERNAL'
    OTHER = 'OTHER'


class CompanyType(StrEnum):
    COMPANY = 'COMPANY'
    INDIVIDUAL = 'INDIVIDUAL'
    ORGANIZATION = 'ORGANIZATION'


class ContactType(StrEnum):
    BUSINESS = 'BUSINESS'
    PURCHASE = 'PURCHASE'
    RECEIVING = 'RECEIVING'
    QUALITY = 'QUALITY'
    TECHNICAL = 'TECHNICAL'
    FINANCE = 'FINANCE'
    AFTER_SALES = 'AFTER_SALES'
    OTHER = 'OTHER'


class ContactStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class AddressType(StrEnum):
    REGISTERED = 'REGISTERED'
    OFFICE = 'OFFICE'
    DELIVERY = 'DELIVERY'
    RETURN = 'RETURN'
    BILLING = 'BILLING'
    OTHER = 'OTHER'


class AddressStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'
