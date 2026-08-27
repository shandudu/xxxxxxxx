from datetime import datetime
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped,mapped_column
from backend.common.model import Base,TimeZone,UniversalText,id_key
from backend.plugin.sales.enums import SalesOrderStatus,ShipmentStatus

class SalesOrder(Base):
    """ERP sales order with customer snapshot."""
    __tablename__='erp_sales_order'
    __table_args__=(sa.ForeignKeyConstraint(['customer_id'],['erp_customer.id'],name='fk_sales_order_customer'),sa.UniqueConstraint('sales_order_no','deleted',name='uk_erp_sales_order_no'),sa.Index('idx_erp_sales_order_status','status'),{'comment':'ERP sales orders'})
    id:Mapped[id_key]=mapped_column(init=False)
    sales_order_no:Mapped[str]=mapped_column(sa.String(100));customer_id:Mapped[int]=mapped_column(sa.BigInteger)
    customer_code_snapshot:Mapped[str]=mapped_column(sa.String(80));customer_name_snapshot:Mapped[str]=mapped_column(sa.String(200))
    status:Mapped[SalesOrderStatus]=mapped_column(sa.String(30),default=SalesOrderStatus.DRAFT,server_default=SalesOrderStatus.DRAFT.value)
    requested_delivery_at:Mapped[datetime|None]=mapped_column(sa.DateTime(timezone=True),default=None)
    currency:Mapped[str]=mapped_column(sa.String(10),default='CNY',server_default='CNY');remark:Mapped[str|None]=mapped_column(UniversalText,default=None)
class SalesOrderLine(Base):
    """ERP sales order material line."""
    __tablename__='erp_sales_order_line'
    __table_args__=(sa.ForeignKeyConstraint(['sales_order_id'],['erp_sales_order.id'],name='fk_sales_order_line_header'),sa.ForeignKeyConstraint(['material_id'],['mes_material.id'],name='fk_sales_order_line_material'),sa.ForeignKeyConstraint(['unit_id'],['mes_unit.id'],name='fk_sales_order_line_unit'),sa.UniqueConstraint('sales_order_id','line_no','deleted',name='uk_erp_sales_order_line_no'),{'comment':'ERP sales order lines'})
    id:Mapped[id_key]=mapped_column(init=False);sales_order_id:Mapped[int]=mapped_column(sa.BigInteger);line_no:Mapped[int]=mapped_column();material_id:Mapped[int]=mapped_column(sa.BigInteger);unit_id:Mapped[int]=mapped_column(sa.BigInteger);ordered_quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6));material_code_snapshot:Mapped[str]=mapped_column(sa.String(80));material_name_snapshot:Mapped[str]=mapped_column(sa.String(200));unit_code_snapshot:Mapped[str]=mapped_column(sa.String(20));shipped_quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6),default=Decimal('0'),server_default='0');unit_price:Mapped[Decimal|None]=mapped_column(sa.Numeric(18,6),default=None)
class Shipment(Base):
    """Posted customer shipment header."""
    __tablename__='erp_shipment'
    __table_args__=(sa.ForeignKeyConstraint(['sales_order_id'],['erp_sales_order.id'],name='fk_shipment_order'),sa.ForeignKeyConstraint(['customer_id'],['erp_customer.id'],name='fk_shipment_customer'),sa.UniqueConstraint('shipment_no','deleted',name='uk_erp_shipment_no'),{'comment':'ERP customer shipments'})
    id:Mapped[id_key]=mapped_column(init=False);shipment_no:Mapped[str]=mapped_column(sa.String(100));sales_order_id:Mapped[int]=mapped_column(sa.BigInteger);customer_id:Mapped[int]=mapped_column(sa.BigInteger);customer_code_snapshot:Mapped[str]=mapped_column(sa.String(80));customer_name_snapshot:Mapped[str]=mapped_column(sa.String(200));status:Mapped[ShipmentStatus]=mapped_column(sa.String(20),default=ShipmentStatus.POSTED,server_default=ShipmentStatus.POSTED.value);delivered_at:Mapped[datetime|None]=mapped_column(TimeZone,default=None);remark:Mapped[str|None]=mapped_column(UniversalText,default=None)
class ShipmentLine(Base):
    """Shipment stock position, lot and immutable transaction link."""
    __tablename__='erp_shipment_line'
    __table_args__=(sa.ForeignKeyConstraint(['shipment_id'],['erp_shipment.id'],name='fk_shipment_line_header'),sa.ForeignKeyConstraint(['sales_order_line_id'],['erp_sales_order_line.id'],name='fk_shipment_line_order_line'),sa.ForeignKeyConstraint(['material_id'],['mes_material.id'],name='fk_shipment_line_material'),sa.ForeignKeyConstraint(['lot_id'],['mes_material_lot.id'],name='fk_shipment_line_lot'),sa.ForeignKeyConstraint(['warehouse_id'],['mes_warehouse.id'],name='fk_shipment_line_warehouse'),sa.ForeignKeyConstraint(['location_id'],['mes_location.id'],name='fk_shipment_line_location'),sa.ForeignKeyConstraint(['stock_transaction_id'],['mes_stock_transaction.id'],name='fk_shipment_line_stock_tx'),sa.UniqueConstraint('shipment_id','line_no','deleted',name='uk_erp_shipment_line_no'),{'comment':'ERP shipment lines'})
    id:Mapped[id_key]=mapped_column(init=False);shipment_id:Mapped[int]=mapped_column(sa.BigInteger);sales_order_line_id:Mapped[int]=mapped_column(sa.BigInteger);line_no:Mapped[int]=mapped_column();material_id:Mapped[int]=mapped_column(sa.BigInteger);warehouse_id:Mapped[int]=mapped_column(sa.BigInteger);location_id:Mapped[int]=mapped_column(sa.BigInteger);quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6));stock_transaction_id:Mapped[int]=mapped_column(sa.BigInteger);lot_id:Mapped[int|None]=mapped_column(sa.BigInteger,default=None);lot_no_snapshot:Mapped[str|None]=mapped_column(sa.String(100),default=None)

class SalesOrderDeliveryPerformance(Base):
    __tablename__='erp_sales_order_delivery_performance'
    __table_args__=(sa.ForeignKeyConstraint(['sales_order_id'],['erp_sales_order.id'],name='fk_delivery_perf_order'),sa.ForeignKeyConstraint(['sales_order_line_id'],['erp_sales_order_line.id'],name='fk_delivery_perf_line'),sa.ForeignKeyConstraint(['material_id'],['mes_material.id'],name='fk_delivery_perf_material'),sa.ForeignKeyConstraint(['last_shipment_id'],['erp_shipment.id'],name='fk_delivery_perf_shipment'),sa.UniqueConstraint('sales_order_line_id','deleted',name='uk_delivery_perf_line'),sa.Index('idx_delivery_perf_status','otif_status'),sa.Index('idx_delivery_perf_promised','promised_delivery_at'),{'comment':'ERP sales order delivery OTIF performance'})
    id:Mapped[id_key]=mapped_column(init=False);sales_order_id:Mapped[int]=mapped_column(sa.BigInteger);sales_order_line_id:Mapped[int]=mapped_column(sa.BigInteger);material_id:Mapped[int]=mapped_column(sa.BigInteger);promised_delivery_at:Mapped[datetime]=mapped_column(TimeZone);assessed_at:Mapped[datetime]=mapped_column(TimeZone);ordered_quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6));actual_delivery_at:Mapped[datetime|None]=mapped_column(TimeZone,default=None);shipped_quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6),default=Decimal('0'),server_default='0');on_time:Mapped[bool]=mapped_column(default=False,server_default=sa.false());in_full:Mapped[bool]=mapped_column(default=False,server_default=sa.false());otif_status:Mapped[str]=mapped_column(sa.String(30),default='OPEN',server_default='OPEN');delay_reason:Mapped[str|None]=mapped_column(sa.String(30),default=None);last_shipment_id:Mapped[int|None]=mapped_column(sa.BigInteger,default=None)
