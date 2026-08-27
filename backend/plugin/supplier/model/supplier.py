from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, DataClassBase, TimeZone, UniversalText, id_key
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
from backend.utils.timezone import timezone


class SupplierCategory(Base):
    """Hierarchical supplier category."""

    __tablename__ = 'erp_supplier_category'
    __table_args__ = (
        sa.ForeignKeyConstraint(['parent_id'], ['erp_supplier_category.id'], name='fk_erp_supplier_category_parent'),
        sa.UniqueConstraint('category_code', name='uk_erp_supplier_category_code'),
        sa.Index('idx_erp_supplier_category_parent', 'parent_id'),
        sa.Index('idx_erp_supplier_category_status', 'status'),
        {'comment': 'ERP supplier category tree'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    category_code: Mapped[str] = mapped_column(sa.String(50))
    category_name: Mapped[str] = mapped_column(sa.String(100))
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[SupplierCategoryStatus] = mapped_column(
        sa.String(20), default=SupplierCategoryStatus.ACTIVE, server_default=SupplierCategoryStatus.ACTIVE.value
    )
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class Supplier(Base):
    """Supplier master data; operational status, cooperation and quality states are independent."""

    __tablename__ = 'erp_supplier'
    __table_args__ = (
        sa.ForeignKeyConstraint(['category_id'], ['erp_supplier_category.id'], name='fk_erp_supplier_category'),
        sa.UniqueConstraint('supplier_code', name='uk_erp_supplier_code'),
        sa.UniqueConstraint('unified_social_credit_code', name='uk_erp_supplier_credit'),
        sa.Index('idx_erp_supplier_category', 'category_id'),
        sa.Index('idx_erp_supplier_status', 'status'),
        sa.Index('idx_erp_supplier_cooperation', 'cooperation_status'),
        sa.Index('idx_erp_supplier_quality', 'quality_status'),
        sa.Index('idx_erp_supplier_name', 'supplier_name'),
        {'comment': 'ERP supplier master data'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_code: Mapped[str] = mapped_column(sa.String(80))
    supplier_name: Mapped[str] = mapped_column(sa.String(200))
    category_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_type: Mapped[SupplierType] = mapped_column(sa.String(30))
    company_type: Mapped[CompanyType] = mapped_column(sa.String(30))
    short_name: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    unified_social_credit_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    tax_number: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    registered_address: Mapped[str | None] = mapped_column(sa.String(300), default=None)
    business_address: Mapped[str | None] = mapped_column(sa.String(300), default=None)
    website: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    country: Mapped[str | None] = mapped_column(sa.String(60), default=None)
    province: Mapped[str | None] = mapped_column(sa.String(60), default=None)
    city: Mapped[str | None] = mapped_column(sa.String(60), default=None)
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    payment_terms: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    default_lead_time_days: Mapped[int | None] = mapped_column(sa.Integer, default=None)
    purchasing_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    quality_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    trace_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    preferred: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    status: Mapped[SupplierStatus] = mapped_column(
        sa.String(20), default=SupplierStatus.ACTIVE, server_default=SupplierStatus.ACTIVE.value
    )
    cooperation_status: Mapped[CooperationStatus] = mapped_column(
        sa.String(20), default=CooperationStatus.NORMAL, server_default=CooperationStatus.NORMAL.value
    )
    quality_status: Mapped[SupplierQualityStatus] = mapped_column(
        sa.String(20), default=SupplierQualityStatus.QUALIFIED, server_default=SupplierQualityStatus.QUALIFIED.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class SupplierContact(Base):
    """A supplier contact. The service guarantees at most one primary contact per supplier."""

    __tablename__ = 'erp_supplier_contact'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_erp_supplier_contact_supplier'),
        sa.Index('idx_erp_supplier_contact_supplier', 'supplier_id'),
        sa.Index('idx_erp_supplier_contact_primary', 'supplier_id', 'is_primary'),
        {'comment': 'ERP supplier contacts'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    contact_name: Mapped[str] = mapped_column(sa.String(80))
    contact_type: Mapped[ContactType] = mapped_column(sa.String(30))
    department: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    position: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    mobile: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    telephone: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    email: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    wechat: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    is_primary: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    status: Mapped[ContactStatus] = mapped_column(
        sa.String(20), default=ContactStatus.ACTIVE, server_default=ContactStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierMaterial(Base):
    """Approved supplier-to-material relationship without duplicating the material master."""

    __tablename__ = 'erp_supplier_material'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_erp_supplier_material_supplier'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_erp_supplier_material_material'),
        sa.UniqueConstraint('supplier_id', 'material_id', name='uk_erp_supplier_material'),
        sa.Index('idx_erp_supplier_material_supplier', 'supplier_id'),
        sa.Index('idx_erp_supplier_material_material', 'material_id'),
        sa.Index('idx_erp_supplier_material_status', 'status'),
        {'comment': 'ERP supplier material relationship'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_material_code: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    supplier_material_name: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    status: Mapped[SupplierMaterialStatus] = mapped_column(
        sa.String(20), default=SupplierMaterialStatus.ACTIVE, server_default=SupplierMaterialStatus.ACTIVE.value
    )
    preferred: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    minimum_order_quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    lead_time_days: Mapped[int | None] = mapped_column(sa.Integer, default=None)
    quality_inspection_required: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierOperationLog(DataClassBase):
    """Immutable object-level audit log for supplier master-data changes."""

    __tablename__ = 'erp_supplier_operation_log'
    __table_args__ = (
        sa.Index('idx_erp_supplier_operation_supplier', 'supplier_id', 'created_time'),
        sa.Index('idx_erp_supplier_operation_object', 'object_type', 'object_id'),
        {'comment': 'ERP supplier operation audit log'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    object_type: Mapped[str] = mapped_column(sa.String(40))
    action: Mapped[str] = mapped_column(sa.String(40))
    supplier_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    supplier_code: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    object_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    object_code: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    before_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    after_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    created_time: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now)
