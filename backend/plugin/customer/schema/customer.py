from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase
from backend.plugin.customer.enums import (
    AddressStatus, AddressType, CompanyType, ContactStatus, ContactType, CooperationStatus,
    CustomerCategoryStatus, CustomerStatus, CustomerType,
)

CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def _code(value: Any) -> str:
    return str(value).strip().upper()


def _text(value: Any) -> str:
    return str(value).strip()


class _TextSchema(SchemaBase):
    @field_validator('*', mode='before')
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        return _text(value) if isinstance(value, str) else value


class CustomerCategoryConfig(_TextSchema):
    category_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    category_name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = Field(None, ge=1)
    status: CustomerCategoryStatus = CustomerCategoryStatus.ACTIVE
    sort_no: int = 0
    remark: str | None = Field(None, max_length=500)

    @field_validator('category_code', mode='before')
    @classmethod
    def normalize_code(cls, value: Any) -> str:
        return _code(value)


class CreateCustomerCategoryParam(CustomerCategoryConfig):
    pass


class UpdateCustomerCategoryParam(CustomerCategoryConfig):
    pass


class CustomerCategoryDetail(CustomerCategoryConfig):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_time: datetime
    updated_time: datetime | None = None


class CustomerCategoryTreeNode(SchemaBase):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    status: CustomerCategoryStatus
    sort_no: int
    remark: str | None = None
    children: list['CustomerCategoryTreeNode'] = Field(default_factory=list)


class CustomerConfig(_TextSchema):
    customer_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    customer_name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(None, max_length=100)
    category_id: int | None = Field(None, ge=1)
    customer_type: CustomerType
    company_type: CompanyType | None = None
    unified_social_credit_code: str | None = Field(None, max_length=50)
    tax_number: str | None = Field(None, max_length=50)
    country: str | None = Field(None, max_length=80)
    province: str | None = Field(None, max_length=80)
    city: str | None = Field(None, max_length=80)
    registered_address: str | None = Field(None, max_length=500)
    website: str | None = Field(None, max_length=200)
    status: CustomerStatus = CustomerStatus.ACTIVE
    cooperation_status: CooperationStatus = CooperationStatus.NORMAL
    sales_enabled: bool = True
    shipment_enabled: bool = True
    trace_enabled: bool = True
    preferred: bool = False
    default_currency: str | None = Field(None, max_length=20)
    payment_term: str | None = Field(None, max_length=200)
    delivery_term: str | None = Field(None, max_length=200)
    remark: str | None = Field(None, max_length=1000)

    @field_validator('customer_code', mode='before')
    @classmethod
    def normalize_customer_code(cls, value: Any) -> str:
        return _code(value)

    @field_validator('unified_social_credit_code', 'tax_number', 'default_currency', mode='before')
    @classmethod
    def normalize_uppercase(cls, value: Any) -> Any:
        return _code(value) if value is not None and str(value).strip() else None


class CreateCustomerParam(CustomerConfig):
    pass


class UpdateCustomerParam(CustomerConfig):
    pass


class CustomerStatusParam(SchemaBase):
    status: CustomerStatus


class CooperationStatusParam(_TextSchema):
    cooperation_status: CooperationStatus
    reason: str | None = Field(None, max_length=500)


class CustomerAddressOption(SchemaBase):
    id: int
    code: str
    name: str
    full_address: str
    contact_name: str | None = None
    contact_phone: str | None = None


class CustomerListItem(SchemaBase):
    id: int
    customer_code: str
    customer_name: str
    short_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    customer_type: CustomerType
    company_type: CompanyType | None = None
    unified_social_credit_code: str | None = None
    tax_number: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    registered_address: str | None = None
    website: str | None = None
    status: CustomerStatus
    cooperation_status: CooperationStatus
    sales_enabled: bool
    shipment_enabled: bool
    trace_enabled: bool
    preferred: bool
    default_currency: str | None = None
    payment_term: str | None = None
    delivery_term: str | None = None
    remark: str | None = None
    created_time: datetime
    updated_time: datetime | None = None


class CustomerDetail(CustomerListItem):
    contact_count: int = 0
    address_count: int = 0
    default_delivery_address: CustomerAddressOption | None = None
    created_by: int | None = None
    updated_by: int | None = None


class CustomerOption(SchemaBase):
    id: int
    code: str
    name: str
    short_name: str | None = None
    country: str | None = None
    preferred: bool


class ContactConfig(_TextSchema):
    contact_name: str = Field(min_length=1, max_length=100)
    contact_type: ContactType = ContactType.BUSINESS
    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    mobile: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=150)
    wechat: str | None = Field(None, max_length=100)
    is_primary: bool = False
    status: ContactStatus = ContactStatus.ACTIVE
    remark: str | None = Field(None, max_length=1000)


class CreateCustomerContactParam(ContactConfig):
    pass


class UpdateCustomerContactParam(ContactConfig):
    pass


class ContactStatusParam(SchemaBase):
    status: ContactStatus


class CustomerContactDetail(ContactConfig):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    created_time: datetime
    updated_time: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None


class AddressConfig(_TextSchema):
    address_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    address_name: str = Field(min_length=1, max_length=100)
    address_type: AddressType = AddressType.DELIVERY
    country: str = Field(min_length=1, max_length=80)
    province: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    detail_address: str = Field(min_length=1, max_length=500)
    postal_code: str | None = Field(None, max_length=30)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=50)
    is_default: bool = False
    status: AddressStatus = AddressStatus.ACTIVE
    remark: str | None = Field(None, max_length=1000)

    @field_validator('address_code', mode='before')
    @classmethod
    def normalize_address_code(cls, value: Any) -> str:
        return _code(value)


class CreateCustomerAddressParam(AddressConfig):
    pass


class UpdateCustomerAddressParam(AddressConfig):
    pass


class AddressStatusParam(SchemaBase):
    status: AddressStatus


class CustomerAddressDetail(AddressConfig):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    full_address: str
    created_time: datetime
    updated_time: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
