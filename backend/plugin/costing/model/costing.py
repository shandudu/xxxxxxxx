from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.costing.enums import CostElement, CostPeriodStatus, CostPostingStatus


class CostPeriod(Base):
    __tablename__ = 'erp_cost_period'
    __table_args__ = (
        sa.UniqueConstraint('period_code', 'deleted', name='uk_erp_cost_period_code'),
        sa.Index('idx_erp_cost_period_status', 'status'),
        {'comment': 'ERP production cost accounting period and standard rates'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_code: Mapped[str] = mapped_column(sa.String(20))
    start_date: Mapped[date] = mapped_column(sa.Date)
    end_date: Mapped[date] = mapped_column(sa.Date)
    status: Mapped[CostPeriodStatus] = mapped_column(sa.String(20), default=CostPeriodStatus.OPEN, server_default='OPEN')
    labor_rate_per_hour: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    machine_rate_per_hour: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    overhead_rate_per_hour: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    currency: Mapped[str] = mapped_column(sa.String(10), default='CNY', server_default='CNY')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class MaterialCost(Base):
    __tablename__ = 'erp_material_cost'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_cost_period.id'], name='fk_erp_material_cost_period'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_erp_material_cost_material'),
        sa.UniqueConstraint('period_id', 'material_id', 'deleted', name='uk_erp_material_cost_material'),
        sa.Index('idx_erp_material_cost_period', 'period_id'),
        {'comment': 'ERP period material weighted-average cost'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    source_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    source_amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    source: Mapped[str] = mapped_column(sa.String(30), default='PURCHASE_RECEIPT', server_default='PURCHASE_RECEIPT')
    calculated_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class WorkOrderCost(Base):
    __tablename__ = 'erp_work_order_cost'
    __table_args__ = (
        sa.ForeignKeyConstraint(['period_id'], ['erp_cost_period.id'], name='fk_erp_work_order_cost_period'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_erp_work_order_cost_work_order'),
        sa.ForeignKeyConstraint(['product_material_id'], ['mes_material.id'], name='fk_erp_work_order_cost_product'),
        sa.UniqueConstraint('period_id', 'work_order_id', 'deleted', name='uk_erp_work_order_cost_order'),
        sa.Index('idx_erp_work_order_cost_product', 'product_material_id', 'status'),
        {'comment': 'ERP actual work-order cost trial and settlement'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_no_snapshot: Mapped[str] = mapped_column(sa.String(100))
    product_material_id: Mapped[int] = mapped_column(sa.BigInteger)
    product_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    product_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    material_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    labor_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    machine_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    overhead_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    quality_loss_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    total_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    unit_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[CostPostingStatus] = mapped_column(sa.String(20), default=CostPostingStatus.DRAFT, server_default='DRAFT')
    calculated_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    posted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class WorkOrderCostLine(Base):
    __tablename__ = 'erp_work_order_cost_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_cost_id'], ['erp_work_order_cost.id'], name='fk_erp_work_order_cost_line_header'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_erp_work_order_cost_line_material'),
        sa.Index('idx_erp_work_order_cost_line_header', 'work_order_cost_id'),
        {'comment': 'ERP traceable work-order cost elements'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_order_cost_id: Mapped[int] = mapped_column(sa.BigInteger)
    element: Mapped[CostElement] = mapped_column(sa.String(30))
    source_type: Mapped[str] = mapped_column(sa.String(40))
    description: Mapped[str] = mapped_column(sa.String(250))
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    unit_rate: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
