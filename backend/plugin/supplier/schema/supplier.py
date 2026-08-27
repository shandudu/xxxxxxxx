from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.supplier.enums import (
    CompanyType,
    ContactStatus,
    ContactType,
    CooperationStatus,
    SupplierCategoryStatus,
    SupplierMaterialStatus,
    SupplierQualityStatus,
    SupplierStatus,
    SupplierType,
)


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


def normalize_optional(value: Any) -> Any:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


class SupplierCategoryBase(SchemaBase):
    category_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    category_name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = Field(None, ge=1)
    sort_no: int = Field(0, ge=0)
    remark: str | None = Field(None, max_length=1000)

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
        return normalize_optional(value)


class CreateSupplierCategoryParam(SupplierCategoryBase):
    status: SupplierCategoryStatus = SupplierCategoryStatus.ACTIVE


class UpdateSupplierCategoryParam(SupplierCategoryBase):
    pass


class SupplierCategoryStatusParam(SchemaBase):
    status: SupplierCategoryStatus


class SupplierCategoryDetail(SupplierCategoryBase):
    id: int
    status: SupplierCategoryStatus
    created_time: datetime
    updated_time: datetime | None = None


class SupplierCategoryTreeNode(SchemaBase):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    status: SupplierCategoryStatus
    sort_no: int
    children: list['SupplierCategoryTreeNode'] = Field(default_factory=list)


class SupplierEditableBase(SchemaBase):
    supplier_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    supplier_name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(None, max_length=100)
    category_id: int = Field(ge=1)
    supplier_type: SupplierType
    company_type: CompanyType
    unified_social_credit_code: str | None = Field(None, max_length=50)
    tax_number: str | None = Field(None, max_length=50)
    registered_address: str | None = Field(None, max_length=300)
    business_address: str | None = Field(None, max_length=300)
    website: str | None = Field(None, max_length=200)
    country: str | None = Field(None, max_length=60)
    province: str | None = Field(None, max_length=60)
    city: str | None = Field(None, max_length=60)
    currency: str = Field('CNY', min_length=1, max_length=10)
    payment_terms: str | None = Field(None, max_length=100)
    default_lead_time_days: int | None = Field(None, ge=0)
    purchasing_enabled: bool = True
    quality_enabled: bool = True
    trace_enabled: bool = True
    preferred: bool = False
    remark: str | None = Field(None, max_length=2000)

    @field_validator('supplier_code', mode='before')
    @classmethod
    def normalize_supplier_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('supplier_name', mode='before')
    @classmethod
    def normalize_supplier_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator(
        'short_name', 'unified_social_credit_code', 'tax_number', 'registered_address', 'business_address',
        'website', 'country', 'province', 'city', 'payment_terms', 'remark', mode='before'
    )
    @classmethod
    def normalize_supplier_optional_fields(cls, value: Any) -> Any:
        return normalize_optional(value)

    @field_validator('currency', mode='before')
    @classmethod
    def normalize_currency(cls, value: Any) -> str:
        return normalize_code(value)


class CreateSupplierParam(SupplierEditableBase):
    status: SupplierStatus = SupplierStatus.ACTIVE
    cooperation_status: CooperationStatus = CooperationStatus.NORMAL
    quality_status: SupplierQualityStatus = SupplierQualityStatus.QUALIFIED


class UpdateSupplierParam(SupplierEditableBase):
    pass


class SupplierStatusParam(SchemaBase):
    status: SupplierStatus


class SupplierCooperationParam(SchemaBase):
    cooperation_status: CooperationStatus


class SupplierQualityParam(SchemaBase):
    quality_status: SupplierQualityStatus


class SupplierListItem(SchemaBase):
    id: int
    supplier_code: str
    supplier_name: str
    short_name: str | None = None
    category_id: int
    category_name: str | None = None
    supplier_type: SupplierType
    company_type: CompanyType
    status: SupplierStatus
    cooperation_status: CooperationStatus
    quality_status: SupplierQualityStatus
    purchasing_enabled: bool
    preferred: bool
    default_lead_time_days: int | None = None
    created_time: datetime
    updated_time: datetime | None = None


class SupplierDetail(SupplierListItem):
    unified_social_credit_code: str | None = None
    tax_number: str | None = None
    registered_address: str | None = None
    business_address: str | None = None
    website: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    currency: str
    payment_terms: str | None = None
    quality_enabled: bool
    trace_enabled: bool
    remark: str | None = None


class SupplierOption(SchemaBase):
    id: int
    code: str
    name: str
    short_name: str | None = None
    category_id: int
    preferred: bool


class SupplierContactBase(SchemaBase):
    contact_name: str = Field(min_length=1, max_length=80)
    contact_type: ContactType
    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    mobile: str | None = Field(None, max_length=50)
    telephone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=120)
    wechat: str | None = Field(None, max_length=80)
    is_primary: bool = False
    remark: str | None = Field(None, max_length=1000)

    @field_validator('contact_name', mode='before')
    @classmethod
    def normalize_contact_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('department', 'position', 'mobile', 'telephone', 'email', 'wechat', 'remark', mode='before')
    @classmethod
    def normalize_contact_optional_fields(cls, value: Any) -> Any:
        return normalize_optional(value)


class CreateSupplierContactParam(SupplierContactBase):
    status: ContactStatus = ContactStatus.ACTIVE


class UpdateSupplierContactParam(SupplierContactBase):
    pass


class SupplierContactStatusParam(SchemaBase):
    status: ContactStatus


class SupplierContactDetail(SupplierContactBase):
    id: int
    supplier_id: int
    status: ContactStatus
    created_time: datetime
    updated_time: datetime | None = None


class SupplierMaterialBase(SchemaBase):
    material_id: int = Field(ge=1)
    supplier_material_code: str | None = Field(None, max_length=100)
    supplier_material_name: str | None = Field(None, max_length=200)
    preferred: bool = False
    minimum_order_quantity: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=6)
    lead_time_days: int | None = Field(None, ge=0)
    quality_inspection_required: bool = False
    remark: str | None = Field(None, max_length=1000)

    @field_validator('supplier_material_code', mode='before')
    @classmethod
    def normalize_supplier_material_code(cls, value: Any) -> Any:
        return normalize_optional(value)

    @field_validator('supplier_material_name', 'remark', mode='before')
    @classmethod
    def normalize_supplier_material_optional_fields(cls, value: Any) -> Any:
        return normalize_optional(value)


class CreateSupplierMaterialParam(SupplierMaterialBase):
    status: SupplierMaterialStatus = SupplierMaterialStatus.ACTIVE


class UpdateSupplierMaterialParam(SupplierMaterialBase):
    pass


class SupplierMaterialStatusParam(SchemaBase):
    status: SupplierMaterialStatus


class SupplierMaterialDetail(SupplierMaterialBase):
    id: int
    supplier_id: int
    status: SupplierMaterialStatus
    material_code: str | None = None
    material_name: str | None = None
    material_specification: str | None = None
    unit: str | None = None
    created_time: datetime
    updated_time: datetime | None = None
