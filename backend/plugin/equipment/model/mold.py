from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.equipment.enums import (
    MoldCavityStatus, MoldCostType, MoldMaintenanceStatus, MoldMaintenanceTrigger,
    MoldMaintenanceType, MoldMountStatus, MoldQualityResult, MoldStatus,
)


class MoldAsset(Base):
    """Mold master record with shot-based life and maintenance counters."""
    __tablename__ = 'mes_mold_asset'
    __table_args__ = (
        sa.ForeignKeyConstraint(['tool_equipment_id'], ['mes_equipment.id'], name='fk_mold_tool_equipment'),
        sa.ForeignKeyConstraint(['product_material_id'], ['mes_material.id'], name='fk_mold_product_material'),
        sa.ForeignKeyConstraint(['mounted_equipment_id'], ['mes_equipment.id'], name='fk_mold_mounted_equipment'),
        sa.UniqueConstraint('mold_code', 'deleted', name='uk_mes_mold_code'),
        sa.UniqueConstraint('tool_equipment_id', 'deleted', name='uk_mes_mold_tool_equipment'),
        sa.Index('idx_mes_mold_status', 'status'),
        sa.Index('idx_mes_mold_product', 'product_material_id'),
        sa.Index('idx_mes_mold_life', 'current_shots', 'designed_life_shots'),
        {'comment': 'MES mold lifecycle master'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    mold_code: Mapped[str] = mapped_column(sa.String(100))
    mold_name: Mapped[str] = mapped_column(sa.String(200))
    tool_equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    product_material_id: Mapped[int] = mapped_column(sa.BigInteger)
    mold_type: Mapped[str] = mapped_column(sa.String(50))
    cavity_count: Mapped[int] = mapped_column(sa.Integer)
    designed_life_shots: Mapped[int] = mapped_column(sa.BigInteger)
    maintenance_interval_shots: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[MoldStatus] = mapped_column(sa.String(20), default=MoldStatus.AVAILABLE, server_default='AVAILABLE')
    warning_percent: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('90'), server_default='90')
    current_shots: Mapped[int] = mapped_column(sa.BigInteger, default=0, server_default='0')
    shots_since_maintenance: Mapped[int] = mapped_column(sa.BigInteger, default=0, server_default='0')
    mounted_equipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    acquisition_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    residual_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    commission_date: Mapped[date | None] = mapped_column(sa.Date, default=None)
    last_maintenance_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    next_maintenance_shots: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    location: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    manufacturer: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MoldCavity(Base):
    """Individual mold cavity condition and quality counters."""
    __tablename__ = 'mes_mold_cavity'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_cavity_mold'),
        sa.UniqueConstraint('mold_id', 'cavity_no', 'deleted', name='uk_mold_cavity_no'),
        sa.Index('idx_mold_cavity_status', 'mold_id', 'status'),
        {'comment': 'MES mold cavity quality state'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    cavity_no: Mapped[str] = mapped_column(sa.String(40))
    status: Mapped[MoldCavityStatus] = mapped_column(sa.String(20), default=MoldCavityStatus.ACTIVE, server_default='ACTIVE')
    current_shots: Mapped[int] = mapped_column(sa.BigInteger, default=0, server_default='0')
    inspected_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    defect_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    last_defect_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    last_defect_code: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MoldMountRecord(Base):
    """Mold mounting/unmounting record bound to a machine and optional work order."""
    __tablename__ = 'mes_mold_mount_record'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_mount_mold'),
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_mold_mount_equipment'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_mount_work_order'),
        sa.UniqueConstraint('mount_no', 'deleted', name='uk_mold_mount_no'),
        sa.Index('idx_mold_mount_active', 'mold_id', 'status'),
        sa.Index('idx_mold_mount_work_order', 'work_order_id', 'status'),
        {'comment': 'MES mold mounting history'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    mount_no: Mapped[str] = mapped_column(sa.String(100))
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    mounted_at: Mapped[datetime] = mapped_column(TimeZone)
    opening_shots: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[MoldMountStatus] = mapped_column(sa.String(20), default=MoldMountStatus.MOUNTED, server_default='MOUNTED')
    work_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    mounted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    unmounted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    unmounted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    closing_shots: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    produced_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MoldUsageRecord(Base):
    """Idempotent mold shot posting derived from one production report."""
    __tablename__ = 'mes_mold_usage_record'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_usage_mold'),
        sa.ForeignKeyConstraint(['mount_id'], ['mes_mold_mount_record.id'], name='fk_mold_usage_mount'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_usage_work_order'),
        sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_mold_usage_report'),
        sa.UniqueConstraint('production_report_id', 'deleted', name='uk_mold_usage_report'),
        sa.Index('idx_mold_usage_mold_time', 'mold_id', 'reported_at'),
        {'comment': 'MES mold shot usage from production reporting'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    mount_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    production_report_id: Mapped[int] = mapped_column(sa.BigInteger)
    shot_count: Mapped[int] = mapped_column(sa.BigInteger)
    active_cavity_count: Mapped[int] = mapped_column(sa.Integer)
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    reported_at: Mapped[datetime] = mapped_column(TimeZone)


class MoldMaintenanceOrder(Base):
    """Shot/time/quality/fault-triggered mold maintenance or repair order."""
    __tablename__ = 'mes_mold_maintenance_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_maintenance_mold'),
        sa.ForeignKeyConstraint(['repair_order_id'], ['mes_repair_order.id'], name='fk_mold_maintenance_repair'),
        sa.UniqueConstraint('order_no', 'deleted', name='uk_mold_maintenance_no'),
        sa.Index('idx_mold_maintenance_status_due', 'status', 'due_at'),
        sa.Index('idx_mold_maintenance_mold', 'mold_id', 'status'),
        {'comment': 'MES mold maintenance and repair orders'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    order_no: Mapped[str] = mapped_column(sa.String(100))
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    maintenance_type: Mapped[MoldMaintenanceType] = mapped_column(sa.String(20))
    trigger_type: Mapped[MoldMaintenanceTrigger] = mapped_column(sa.String(20))
    description: Mapped[str] = mapped_column(UniversalText)
    status: Mapped[MoldMaintenanceStatus] = mapped_column(sa.String(20), default=MoldMaintenanceStatus.PLANNED, server_default='PLANNED')
    due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    due_shots: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    repair_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    findings: Mapped[str | None] = mapped_column(UniversalText, default=None)
    action_taken: Mapped[str | None] = mapped_column(UniversalText, default=None)
    labor_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    material_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    external_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    total_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MoldCavityQualityRecord(Base):
    """Cavity-level inspection result that can automatically block a cavity."""
    __tablename__ = 'mes_mold_cavity_quality_record'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_quality_mold'),
        sa.ForeignKeyConstraint(['cavity_id'], ['mes_mold_cavity.id'], name='fk_mold_quality_cavity'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_quality_work_order'),
        sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_mold_quality_report'),
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_mold_quality_inspection'),
        sa.Index('idx_mold_quality_cavity_time', 'cavity_id', 'checked_at'),
        sa.Index('idx_mold_quality_result', 'result'),
        {'comment': 'MES mold cavity quality records'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    cavity_id: Mapped[int] = mapped_column(sa.BigInteger)
    inspected_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    defect_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    result: Mapped[MoldQualityResult] = mapped_column(sa.String(20))
    checked_at: Mapped[datetime] = mapped_column(TimeZone)
    work_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    production_report_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    inspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    defect_code: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MoldCostLedger(Base):
    """Immutable mold lifecycle cost entry."""
    __tablename__ = 'mes_mold_cost_ledger'
    __table_args__ = (
        sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_cost_mold'),
        sa.UniqueConstraint('entry_no', 'deleted', name='uk_mold_cost_no'),
        sa.Index('idx_mold_cost_mold_time', 'mold_id', 'occurred_at'),
        {'comment': 'MES mold lifecycle cost ledger'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    entry_no: Mapped[str] = mapped_column(sa.String(100))
    mold_id: Mapped[int] = mapped_column(sa.BigInteger)
    cost_type: Mapped[MoldCostType] = mapped_column(sa.String(20))
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    occurred_at: Mapped[datetime] = mapped_column(TimeZone)
    source_type: Mapped[str | None] = mapped_column(sa.String(40), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
