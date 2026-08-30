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


class SupplierQualificationStatus(StrEnum):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    UNDER_REVIEW = 'UNDER_REVIEW'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    SUSPENDED = 'SUSPENDED'
    REMOVED = 'REMOVED'


class SupplierAuditType(StrEnum):
    INITIAL = 'INITIAL'
    PERIODIC = 'PERIODIC'
    SPECIAL = 'SPECIAL'


class SupplierAuditStatus(StrEnum):
    PLANNED = 'PLANNED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class SupplierAuditResult(StrEnum):
    PASS = 'PASS'
    CONDITIONAL = 'CONDITIONAL'
    FAIL = 'FAIL'


class SupplierSampleStatus(StrEnum):
    PENDING = 'PENDING'
    TESTING = 'TESTING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'


class SupplierPpapStatus(StrEnum):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'


class SupplierAvlStatus(StrEnum):
    APPROVED = 'APPROVED'
    CONDITIONAL = 'CONDITIONAL'
    SUSPENDED = 'SUSPENDED'
    REMOVED = 'REMOVED'


class SupplierReviewStatus(StrEnum):
    PLANNED = 'PLANNED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class SupplierReviewDecision(StrEnum):
    CONTINUE = 'CONTINUE'
    CONDITIONAL = 'CONDITIONAL'
    SUSPEND = 'SUSPEND'
    REMOVE = 'REMOVE'
