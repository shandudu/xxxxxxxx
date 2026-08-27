from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.planning.enums import (
    MpsDemandType,
    MpsPlanStatus,
    MrpRunStatus,
    PlannedOrderStatus,
    PlannedOrderType,
)
from backend.utils.timezone import timezone


class MpsPlan(Base):
    """Versioned master production schedule header."""

    __tablename__ = 'mes_mps_plan'
    __table_args__ = (
        sa.UniqueConstraint('plan_no', 'deleted', name='uk_mes_mps_plan_no_deleted'),
        sa.Index('idx_mes_mps_plan_status', 'status'),
        sa.Index('idx_mes_mps_plan_horizon', 'horizon_start', 'horizon_end'),
        {'comment': 'MES master production schedule'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    plan_no: Mapped[str] = mapped_column(sa.String(100))
    plan_name: Mapped[str] = mapped_column(sa.String(200))
    horizon_start: Mapped[date] = mapped_column(sa.Date)
    horizon_end: Mapped[date] = mapped_column(sa.Date)
    status: Mapped[MpsPlanStatus] = mapped_column(
        sa.String(20), default=MpsPlanStatus.DRAFT, server_default=MpsPlanStatus.DRAFT.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class MpsDemand(Base):
    """Time-phased independent demand in an MPS plan."""

    __tablename__ = 'mes_mps_demand'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mps_plan_id'], ['mes_mps_plan.id'], name='fk_mps_demand_plan'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_mps_demand_material'),
        sa.ForeignKeyConstraint(['unit_id'], ['mes_unit.id'], name='fk_mps_demand_unit'),
        sa.UniqueConstraint('mps_plan_id', 'line_no', 'deleted', name='uk_mes_mps_demand_line'),
        sa.Index('idx_mes_mps_demand_material_date', 'material_id', 'demand_date'),
        sa.Index('idx_mes_mps_demand_source', 'demand_type', 'source_id'),
        {'comment': 'MES time-phased independent demand'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    mps_plan_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column(sa.Integer)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    unit_id: Mapped[int] = mapped_column(sa.BigInteger)
    demand_date: Mapped[date] = mapped_column(sa.Date)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_code_snapshot: Mapped[str] = mapped_column(sa.String(20))
    demand_type: Mapped[MpsDemandType] = mapped_column(
        sa.String(30), default=MpsDemandType.MANUAL, server_default=MpsDemandType.MANUAL.value
    )
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MrpRun(Base):
    """Immutable parameters and outcome of one MRP calculation."""

    __tablename__ = 'mes_mrp_run'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mps_plan_id'], ['mes_mps_plan.id'], name='fk_mrp_run_plan'),
        sa.UniqueConstraint('run_no', 'deleted', name='uk_mes_mrp_run_no_deleted'),
        sa.Index('idx_mes_mrp_run_plan', 'mps_plan_id'),
        sa.Index('idx_mes_mrp_run_status', 'status'),
        {'comment': 'MES material requirements planning run'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    run_no: Mapped[str] = mapped_column(sa.String(100))
    mps_plan_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[MrpRunStatus] = mapped_column(
        sa.String(20), default=MrpRunStatus.RUNNING, server_default=MrpRunStatus.RUNNING.value
    )
    include_inventory: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    include_open_purchase: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    include_open_production: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    default_purchase_lead_days: Mapped[int] = mapped_column(sa.Integer, default=7, server_default='7')
    default_production_lead_days: Mapped[int] = mapped_column(sa.Integer, default=1, server_default='1')
    max_level: Mapped[int] = mapped_column(sa.Integer, default=20, server_default='20')
    requirement_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    planned_order_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    error_message: Mapped[str | None] = mapped_column(UniversalText, default=None)
    started_at: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    promise_refresh_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    promise_assessment_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class MrpRequirement(Base):
    """One netted requirement row with its supply-allocation snapshot."""

    __tablename__ = 'mes_mrp_requirement'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mrp_run_id'], ['mes_mrp_run.id'], name='fk_mrp_requirement_run'),
        sa.ForeignKeyConstraint(['mps_demand_id'], ['mes_mps_demand.id'], name='fk_mrp_requirement_demand'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_mrp_requirement_material'),
        sa.ForeignKeyConstraint(
            ['parent_material_id'], ['mes_material.id'], name='fk_mrp_requirement_parent_material'
        ),
        sa.ForeignKeyConstraint(['bom_id'], ['mes_bom.id'], name='fk_mrp_requirement_bom'),
        sa.ForeignKeyConstraint(['bom_item_id'], ['mes_bom_item.id'], name='fk_mrp_requirement_bom_item'),
        sa.UniqueConstraint('mrp_run_id', 'sequence_no', 'deleted', name='uk_mes_mrp_requirement_sequence'),
        sa.Index('idx_mes_mrp_requirement_material_date', 'material_id', 'requirement_date'),
        sa.Index('idx_mes_mrp_requirement_level', 'mrp_run_id', 'level_no'),
        {'comment': 'MES time-phased net material requirements'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    mrp_run_id: Mapped[int] = mapped_column(sa.BigInteger)
    sequence_no: Mapped[int] = mapped_column(sa.Integer)
    mps_demand_id: Mapped[int] = mapped_column(sa.BigInteger)
    level_no: Mapped[int] = mapped_column(sa.Integer)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    requirement_date: Mapped[date] = mapped_column(sa.Date)
    gross_requirement: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_code_snapshot: Mapped[str] = mapped_column(sa.String(20))
    source_path: Mapped[str] = mapped_column(sa.String(500))
    on_hand_allocated: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=0, server_default='0')
    purchase_supply_allocated: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 6), default=0, server_default='0'
    )
    production_supply_allocated: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 6), default=0, server_default='0'
    )
    net_requirement: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=0, server_default='0')
    planned_order_quantity: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 6), default=0, server_default='0'
    )
    uncovered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=0, server_default='0')
    parent_material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    bom_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    bom_item_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class PlannedOrder(Base):
    """MRP planned purchase or production order that can be firmed and released."""

    __tablename__ = 'mes_planned_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mrp_run_id'], ['mes_mrp_run.id'], name='fk_planned_order_run'),
        sa.ForeignKeyConstraint(
            ['mrp_requirement_id'], ['mes_mrp_requirement.id'], name='fk_planned_order_requirement'
        ),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_planned_order_material'),
        sa.ForeignKeyConstraint(['bom_id'], ['mes_bom.id'], name='fk_planned_order_bom'),
        sa.UniqueConstraint('planned_order_no', 'deleted', name='uk_mes_planned_order_no_deleted'),
        sa.UniqueConstraint('mrp_run_id', 'sequence_no', 'deleted', name='uk_mes_planned_order_sequence'),
        sa.Index('idx_mes_planned_order_material_date', 'material_id', 'due_date'),
        sa.Index('idx_mes_planned_order_status', 'status'),
        {'comment': 'MES MRP planned orders'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    planned_order_no: Mapped[str] = mapped_column(sa.String(100))
    mrp_run_id: Mapped[int] = mapped_column(sa.BigInteger)
    mrp_requirement_id: Mapped[int] = mapped_column(sa.BigInteger)
    sequence_no: Mapped[int] = mapped_column(sa.Integer)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    order_type: Mapped[PlannedOrderType] = mapped_column(sa.String(20))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    release_date: Mapped[date] = mapped_column(sa.Date)
    due_date: Mapped[date] = mapped_column(sa.Date)
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_code_snapshot: Mapped[str] = mapped_column(sa.String(20))
    status: Mapped[PlannedOrderStatus] = mapped_column(
        sa.String(20), default=PlannedOrderStatus.PLANNED, server_default=PlannedOrderStatus.PLANNED.value
    )
    bom_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_document_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    source_document_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_document_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    firmed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    firmed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    released_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    released_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
