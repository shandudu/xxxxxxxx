from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.performance.enums import TargetStatus


class PerformanceTarget(Base):
    """Configurable OEE targets and optional work-center cycle-time fallback."""

    __tablename__ = 'mes_performance_target'
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['work_center_id'], ['mes_work_center.id'], name='fk_performance_target_center'
        ),
        sa.UniqueConstraint(
            'work_center_id', 'deleted', name='uk_mes_performance_target_center_deleted'
        ),
        sa.Index('idx_mes_performance_target_status', 'status'),
        {'comment': 'MES work-center performance targets'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    availability_target: Mapped[Decimal] = mapped_column(
        sa.Numeric(8, 4), default=Decimal('90'), server_default='90'
    )
    performance_target: Mapped[Decimal] = mapped_column(
        sa.Numeric(8, 4), default=Decimal('95'), server_default='95'
    )
    quality_target: Mapped[Decimal] = mapped_column(
        sa.Numeric(8, 4), default=Decimal('99'), server_default='99'
    )
    oee_target: Mapped[Decimal] = mapped_column(
        sa.Numeric(8, 4), default=Decimal('85'), server_default='85'
    )
    ideal_cycle_seconds: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    status: Mapped[TargetStatus] = mapped_column(
        sa.String(20), default=TargetStatus.ACTIVE, server_default=TargetStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class PerformanceSnapshot(Base):
    """Rebuildable daily work-center OEE and reliability snapshot."""

    __tablename__ = 'mes_performance_snapshot'
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['work_center_id'], ['mes_work_center.id'], name='fk_performance_snapshot_center'
        ),
        sa.UniqueConstraint(
            'metric_date', 'work_center_id', 'deleted', name='uk_mes_performance_snapshot_day_center'
        ),
        sa.Index('idx_mes_performance_snapshot_date', 'metric_date'),
        sa.Index('idx_mes_performance_snapshot_center_date', 'work_center_id', 'metric_date'),
        {'comment': 'MES daily work-center performance snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    metric_date: Mapped[date] = mapped_column(sa.Date())
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    calendar_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    planned_downtime_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    planned_production_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    unplanned_downtime_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    operating_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    actual_run_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    idle_capacity_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    total_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    ideal_run_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(24, 4))
    availability_rate: Mapped[Decimal] = mapped_column(sa.Numeric(10, 4))
    performance_rate: Mapped[Decimal] = mapped_column(sa.Numeric(10, 4))
    quality_rate: Mapped[Decimal] = mapped_column(sa.Numeric(10, 4))
    oee_rate: Mapped[Decimal] = mapped_column(sa.Numeric(10, 4))
    utilization_rate: Mapped[Decimal] = mapped_column(sa.Numeric(10, 4))
    actual_cycle_seconds: Mapped[Decimal | None] = mapped_column(sa.Numeric(24, 6))
    ideal_cycle_seconds: Mapped[Decimal | None] = mapped_column(sa.Numeric(24, 6))
    throughput_per_hour: Mapped[Decimal] = mapped_column(sa.Numeric(24, 6))
    failure_count: Mapped[int] = mapped_column(sa.Integer)
    mtbf_minutes: Mapped[Decimal | None] = mapped_column(sa.Numeric(24, 4))
    mttr_minutes: Mapped[Decimal | None] = mapped_column(sa.Numeric(24, 4))
    source_execution_count: Mapped[int] = mapped_column(sa.Integer)
    calculated_at: Mapped[datetime] = mapped_column(TimeZone)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
