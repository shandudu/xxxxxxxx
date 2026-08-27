import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.customer.enums import (
    AddressStatus,
    AddressType,
    CompanyType,
    ContactStatus,
    ContactType,
    CooperationStatus,
    CustomerCategoryStatus,
    CustomerStatus,
    CustomerType,
)


class CustomerCategory(Base):
    __tablename__ = 'erp_customer_category'
    __table_args__ = (
        sa.ForeignKeyConstraint(['parent_id'], ['erp_customer_category.id'], name='fk_erp_customer_category_parent'),
        sa.UniqueConstraint('category_code', 'deleted', name='uk_erp_customer_category_code_deleted'),
        sa.Index('idx_erp_customer_category_parent', 'parent_id'),
        sa.Index('idx_erp_customer_category_status', 'status'),
        {'comment': 'ERP customer category tree'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    category_code: Mapped[str] = mapped_column(sa.String(50), comment='Customer category code')
    category_name: Mapped[str] = mapped_column(sa.String(100), comment='Customer category name')
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[CustomerCategoryStatus] = mapped_column(
        sa.String(20), default=CustomerCategoryStatus.ACTIVE, server_default=CustomerCategoryStatus.ACTIVE.value
    )
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class Customer(Base):
    __tablename__ = 'erp_customer'
    __table_args__ = (
        sa.ForeignKeyConstraint(['category_id'], ['erp_customer_category.id'], name='fk_erp_customer_category'),
        sa.UniqueConstraint('customer_code', 'deleted', name='uk_erp_customer_code_deleted'),
        sa.UniqueConstraint('unified_social_credit_code', 'deleted', name='uk_erp_customer_credit_deleted'),
        sa.Index('idx_erp_customer_category', 'category_id'),
        sa.Index('idx_erp_customer_status', 'status'),
        sa.Index('idx_erp_customer_cooperation', 'cooperation_status'),
        sa.Index('idx_erp_customer_type', 'customer_type'),
        sa.Index('idx_erp_customer_country', 'country'),
        {'comment': 'ERP customer master data'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    customer_code: Mapped[str] = mapped_column(sa.String(80))
    customer_name: Mapped[str] = mapped_column(sa.String(200))
    customer_type: Mapped[CustomerType] = mapped_column(sa.String(30))
    short_name: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    category_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    company_type: Mapped[CompanyType | None] = mapped_column(sa.String(30), default=None)
    unified_social_credit_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    tax_number: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    country: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    province: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    city: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    registered_address: Mapped[str | None] = mapped_column(sa.String(500), default=None)
    website: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    status: Mapped[CustomerStatus] = mapped_column(
        sa.String(20), default=CustomerStatus.ACTIVE, server_default=CustomerStatus.ACTIVE.value
    )
    cooperation_status: Mapped[CooperationStatus] = mapped_column(
        sa.String(20), default=CooperationStatus.NORMAL, server_default=CooperationStatus.NORMAL.value
    )
    sales_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    shipment_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    trace_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    preferred: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    default_currency: Mapped[str | None] = mapped_column(sa.String(20), default=None)
    payment_term: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    delivery_term: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class CustomerContact(Base):
    __tablename__ = 'erp_customer_contact'
    __table_args__ = (
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_erp_customer_contact_customer'),
        sa.Index('idx_erp_customer_contact_customer', 'customer_id'),
        sa.Index('idx_erp_customer_contact_primary', 'customer_id', 'is_primary'),
        {'comment': 'ERP customer contacts'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    contact_name: Mapped[str] = mapped_column(sa.String(100))
    contact_type: Mapped[ContactType] = mapped_column(sa.String(30), default=ContactType.BUSINESS)
    department: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    position: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    phone: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    mobile: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    email: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    wechat: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    is_primary: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    status: Mapped[ContactStatus] = mapped_column(
        sa.String(20), default=ContactStatus.ACTIVE, server_default=ContactStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class CustomerAddress(Base):
    __tablename__ = 'erp_customer_address'
    __table_args__ = (
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_erp_customer_address_customer'),
        sa.UniqueConstraint('customer_id', 'address_code', 'deleted', name='uk_erp_customer_address_code_deleted'),
        sa.Index('idx_erp_customer_address_customer', 'customer_id'),
        sa.Index('idx_erp_customer_address_delivery_default', 'customer_id', 'address_type', 'is_default'),
        {'comment': 'ERP customer addresses'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    address_code: Mapped[str] = mapped_column(sa.String(50))
    address_name: Mapped[str] = mapped_column(sa.String(100))
    country: Mapped[str] = mapped_column(sa.String(80))
    province: Mapped[str] = mapped_column(sa.String(80))
    city: Mapped[str] = mapped_column(sa.String(80))
    district: Mapped[str] = mapped_column(sa.String(80))
    detail_address: Mapped[str] = mapped_column(sa.String(500))
    address_type: Mapped[AddressType] = mapped_column(sa.String(30), default=AddressType.DELIVERY)
    postal_code: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    contact_name: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    contact_phone: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    is_default: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    status: Mapped[AddressStatus] = mapped_column(
        sa.String(20), default=AddressStatus.ACTIVE, server_default=AddressStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
