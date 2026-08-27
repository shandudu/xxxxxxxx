from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.production.enums import MaterialDocumentStatus, WorkOrderOperationStatus, WorkOrderStatus


class WorkOrder(Base):
    """MES work order with immutable BOM, routing and product snapshots."""

    __tablename__ = 'mes_work_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['product_material_id'], ['mes_material.id'], name='fk_work_order_product'),
        sa.ForeignKeyConstraint(['bom_id'], ['mes_bom.id'], name='fk_work_order_bom'),
        sa.ForeignKeyConstraint(['routing_id'], ['mes_routing.id'], name='fk_work_order_routing'),
        sa.UniqueConstraint('work_order_no', 'deleted', name='uk_mes_work_order_no_deleted'),
        sa.Index('idx_mes_work_order_product', 'product_material_id'),
        sa.Index('idx_mes_work_order_status', 'status'),
        {'comment': 'MES production work order'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_order_no: Mapped[str] = mapped_column(sa.String(100))
    product_material_id: Mapped[int] = mapped_column(sa.BigInteger)
    bom_id: Mapped[int] = mapped_column(sa.BigInteger)
    routing_id: Mapped[int] = mapped_column(sa.BigInteger)
    planned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    product_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    product_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    bom_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    bom_version_snapshot: Mapped[str] = mapped_column(sa.String(30))
    routing_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    routing_version_snapshot: Mapped[str] = mapped_column(sa.String(30))
    status: Mapped[WorkOrderStatus] = mapped_column(sa.String(30), default=WorkOrderStatus.DRAFT, server_default=WorkOrderStatus.DRAFT.value)
    completed_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    planned_start_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    planned_end_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class WorkOrderOperation(Base):
    """Routing operation snapshot attached to a work order."""

    __tablename__ = 'mes_work_order_operation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_wo_operation_order'),
        sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_wo_operation_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_wo_operation_center'),
        sa.UniqueConstraint('work_order_id', 'sequence_no', 'deleted', name='uk_mes_wo_operation_sequence'),
        {'comment': 'MES work order operation snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    sequence_no: Mapped[int] = mapped_column()
    operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    operation_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    operation_name_snapshot: Mapped[str] = mapped_column(sa.String(150))
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[WorkOrderOperationStatus] = mapped_column(sa.String(30), default=WorkOrderOperationStatus.PENDING, server_default=WorkOrderOperationStatus.PENDING.value)
    completed_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class WorkOrderMaterialRequirement(Base):
    """Exploded BOM requirement snapshot; optional operation assignment is execution data, not BOM data."""

    __tablename__ = 'mes_work_order_material_requirement'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_wo_requirement_order'),
        sa.ForeignKeyConstraint(['bom_item_id'], ['mes_bom_item.id'], name='fk_wo_requirement_bom_item'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_wo_requirement_material'),
        sa.ForeignKeyConstraint(['unit_id'], ['mes_unit.id'], name='fk_wo_requirement_unit'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_wo_requirement_operation'),
        sa.UniqueConstraint('work_order_id', 'line_no', 'deleted', name='uk_mes_wo_requirement_line'),
        {'comment': 'MES work order material requirement snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    bom_item_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    unit_id: Mapped[int] = mapped_column(sa.BigInteger)
    required_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    work_order_operation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    issued_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    returned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')


class MaterialIssue(Base):
    """Posted production material issue document."""

    __tablename__ = 'mes_material_issue'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_material_issue_order'),
        sa.UniqueConstraint('issue_no', 'deleted', name='uk_mes_material_issue_no'),
        {'comment': 'MES production material issue'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    issue_no: Mapped[str] = mapped_column(sa.String(100))
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[MaterialDocumentStatus] = mapped_column(sa.String(20), default=MaterialDocumentStatus.POSTED, server_default=MaterialDocumentStatus.POSTED.value)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MaterialIssueLine(Base):
    """Posted production issue line and stock transaction link."""

    __tablename__ = 'mes_material_issue_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['issue_id'], ['mes_material_issue.id'], name='fk_material_issue_line_header'),
        sa.ForeignKeyConstraint(['requirement_id'], ['mes_work_order_material_requirement.id'], name='fk_material_issue_line_requirement'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_material_issue_line_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_material_issue_line_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_material_issue_line_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_material_issue_line_location'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_material_issue_line_stock_tx'),
        {'comment': 'MES production issue lines'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    issue_id: Mapped[int] = mapped_column(sa.BigInteger)
    requirement_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    stock_transaction_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    returned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')


class MaterialReturn(Base):
    """Posted production return document."""

    __tablename__ = 'mes_material_return'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_material_return_order'),
        sa.UniqueConstraint('return_no', 'deleted', name='uk_mes_material_return_no'),
        {'comment': 'MES production material return'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    return_no: Mapped[str] = mapped_column(sa.String(100))
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[MaterialDocumentStatus] = mapped_column(sa.String(20), default=MaterialDocumentStatus.POSTED, server_default=MaterialDocumentStatus.POSTED.value)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MaterialReturnLine(Base):
    """Production material return line linked to the original issue."""

    __tablename__ = 'mes_material_return_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['return_id'], ['mes_material_return.id'], name='fk_material_return_line_header'),
        sa.ForeignKeyConstraint(['issue_line_id'], ['mes_material_issue_line.id'], name='fk_material_return_line_issue'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_material_return_line_stock_tx'),
        {'comment': 'MES production material return lines'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    return_id: Mapped[int] = mapped_column(sa.BigInteger)
    issue_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    stock_transaction_id: Mapped[int] = mapped_column(sa.BigInteger)


class ProductionReport(Base):
    """Production completion report and finished-goods stock receipt link."""

    __tablename__ = 'mes_production_report'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_production_report_order'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_production_report_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_production_report_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_production_report_location'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_production_report_stock_tx'),
        sa.UniqueConstraint('report_no', 'deleted', name='uk_mes_production_report_no'),
        {'comment': 'MES production completion reports'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    report_no: Mapped[str] = mapped_column(sa.String(100))
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    stock_transaction_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
