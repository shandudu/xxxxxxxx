from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.purchasing.enums import PurchaseOrderStatus, SupplierReceiptStatus, SupplierReturnStatus


class PurchaseOrder(Base):
    """ERP purchase order header with supplier snapshots."""

    __tablename__ = 'erp_purchase_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_purchase_order_supplier'),
        sa.UniqueConstraint('purchase_order_no', 'deleted', name='uk_erp_purchase_order_no_deleted'),
        sa.Index('idx_erp_purchase_order_supplier', 'supplier_id'),
        sa.Index('idx_erp_purchase_order_status', 'status'),
        {'comment': 'ERP purchase order header'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    purchase_order_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    supplier_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        sa.String(30), default=PurchaseOrderStatus.DRAFT, server_default=PurchaseOrderStatus.DRAFT.value
    )
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class PurchaseOrderLine(Base):
    """ERP purchase order material line."""

    __tablename__ = 'erp_purchase_order_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['purchase_order_id'], ['erp_purchase_order.id'], name='fk_purchase_order_line_header'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_purchase_order_line_material'),
        sa.ForeignKeyConstraint(['unit_id'], ['mes_unit.id'], name='fk_purchase_order_line_unit'),
        sa.UniqueConstraint('purchase_order_id', 'line_no', 'deleted', name='uk_erp_purchase_order_line_no'),
        sa.Index('idx_erp_purchase_order_line_material', 'material_id'),
        {'comment': 'ERP purchase order lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    purchase_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    unit_id: Mapped[int] = mapped_column(sa.BigInteger)
    ordered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_code_snapshot: Mapped[str] = mapped_column(sa.String(20))
    unit_name_snapshot: Mapped[str] = mapped_column(sa.String(50))
    requested_delivery_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    supplier_confirmed_delivery_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    received_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    unit_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierReceipt(Base):
    """Posted supplier receipt header."""

    __tablename__ = 'erp_supplier_receipt'
    __table_args__ = (
        sa.ForeignKeyConstraint(['purchase_order_id'], ['erp_purchase_order.id'], name='fk_supplier_receipt_order'),
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_receipt_supplier'),
        sa.UniqueConstraint('receipt_no', 'deleted', name='uk_erp_supplier_receipt_no_deleted'),
        sa.Index('idx_erp_supplier_receipt_order', 'purchase_order_id'),
        sa.Index('idx_erp_supplier_receipt_supplier', 'supplier_id'),
        {'comment': 'ERP supplier receipt header'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    receipt_no: Mapped[str] = mapped_column(sa.String(100))
    purchase_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    supplier_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    status: Mapped[SupplierReceiptStatus] = mapped_column(
        sa.String(20), default=SupplierReceiptStatus.POSTED, server_default=SupplierReceiptStatus.POSTED.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class SupplierReceiptLine(Base):
    """Supplier receipt line linked to the posted stock transaction."""

    __tablename__ = 'erp_supplier_receipt_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_receipt_id'], ['erp_supplier_receipt.id'], name='fk_supplier_receipt_line_header'),
        sa.ForeignKeyConstraint(['purchase_order_line_id'], ['erp_purchase_order_line.id'], name='fk_supplier_receipt_line_order_line'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_receipt_line_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_supplier_receipt_line_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_supplier_receipt_line_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_supplier_receipt_line_location'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_supplier_receipt_line_stock_tx'),
        sa.UniqueConstraint('supplier_receipt_id', 'line_no', 'deleted', name='uk_erp_supplier_receipt_line_no'),
        sa.Index('idx_erp_supplier_receipt_line_order_line', 'purchase_order_line_id'),
        {'comment': 'ERP supplier receipt lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_receipt_id: Mapped[int] = mapped_column(sa.BigInteger)
    purchase_order_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    warehouse_code_snapshot: Mapped[str] = mapped_column(sa.String(50))
    location_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    stock_transaction_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_no_snapshot: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PurchaseOrderDeliveryPerformance(Base):
    __tablename__ = 'erp_purchase_order_delivery_performance'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_purchase_delivery_supplier'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['erp_purchase_order.id'], name='fk_purchase_delivery_order'),
        sa.ForeignKeyConstraint(['purchase_order_line_id'], ['erp_purchase_order_line.id'], name='fk_purchase_delivery_line'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_purchase_delivery_material'),
        sa.UniqueConstraint('purchase_order_line_id', 'deleted', name='uk_purchase_delivery_line'),
        sa.Index('idx_purchase_delivery_status', 'otif_status'),
        sa.Index('idx_purchase_delivery_supplier', 'supplier_id', 'otif_status'),
        {'comment': 'ERP supplier purchase OTIF performance and shortage impact'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    purchase_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    purchase_order_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    requested_delivery_at: Mapped[datetime] = mapped_column(TimeZone)
    effective_delivery_at: Mapped[datetime] = mapped_column(TimeZone)
    assessed_at: Mapped[datetime] = mapped_column(TimeZone)
    ordered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    supplier_confirmed_delivery_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    actual_delivery_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    received_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    on_time: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    in_full: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    otif_status: Mapped[str] = mapped_column(sa.String(30), default='OPEN', server_default='OPEN')
    delay_reason: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    days_late: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    shortage_impact_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    impacted_sales_order_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    mrp_uncovered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')


class SupplierReturn(Base):
    """Posted supplier return generated by an executed MRB disposition."""

    __tablename__ = 'erp_supplier_return'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_return_supplier'),
        sa.ForeignKeyConstraint(['supplier_receipt_id'], ['erp_supplier_receipt.id'], name='fk_supplier_return_receipt'),
        sa.UniqueConstraint('return_no', 'deleted', name='uk_erp_supplier_return_no'),
        sa.UniqueConstraint('disposition_id', 'deleted', name='uk_erp_supplier_return_disposition'),
        sa.Index('idx_erp_supplier_return_supplier', 'supplier_id'),
        {'comment': 'ERP supplier returns generated from quality MRB'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    return_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_receipt_id: Mapped[int] = mapped_column(sa.BigInteger)
    ncr_id: Mapped[int] = mapped_column(sa.BigInteger)
    disposition_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    supplier_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    status: Mapped[SupplierReturnStatus] = mapped_column(sa.String(20), default=SupplierReturnStatus.POSTED, server_default=SupplierReturnStatus.POSTED.value)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierReturnLine(Base):
    """Supplier return line linked to its outbound inventory transaction."""

    __tablename__ = 'erp_supplier_return_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_return_id'], ['erp_supplier_return.id'], name='fk_supplier_return_line_header'),
        sa.ForeignKeyConstraint(['supplier_receipt_line_id'], ['erp_supplier_receipt_line.id'], name='fk_supplier_return_line_receipt_line'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_return_line_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_supplier_return_line_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_supplier_return_line_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_supplier_return_line_location'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_supplier_return_line_stock_tx'),
        {'comment': 'ERP supplier return lines'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    supplier_return_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    stock_transaction_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_receipt_line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
