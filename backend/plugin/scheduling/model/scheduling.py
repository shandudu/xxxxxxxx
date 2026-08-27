from datetime import date, datetime, time
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.scheduling.enums import (
    ConfigStatus,
    DispatchStatus,
    OperationScheduleStatus,
    ScheduleStatus,
    SchedulingDirection,
)


class Shift(Base):
    """Reusable daily production shift."""

    __tablename__ = 'mes_aps_shift'
    __table_args__ = (
        sa.UniqueConstraint('shift_code', 'deleted', name='uk_mes_aps_shift_code_deleted'),
        sa.Index('idx_mes_aps_shift_status', 'status'),
        {'comment': 'MES APS production shifts'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    shift_code: Mapped[str] = mapped_column(sa.String(50))
    shift_name: Mapped[str] = mapped_column(sa.String(100))
    start_time: Mapped[time] = mapped_column(sa.Time())
    end_time: Mapped[time] = mapped_column(sa.Time())
    spans_next_day: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    break_minutes: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    status: Mapped[ConfigStatus] = mapped_column(
        sa.String(20), default=ConfigStatus.ACTIVE, server_default=ConfigStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class WorkCalendar(Base):
    """Weekly work calendar with optional date overrides."""

    __tablename__ = 'mes_aps_calendar'
    __table_args__ = (
        sa.ForeignKeyConstraint(['default_shift_id'], ['mes_aps_shift.id'], name='fk_aps_calendar_default_shift'),
        sa.UniqueConstraint('calendar_code', 'deleted', name='uk_mes_aps_calendar_code_deleted'),
        sa.Index('idx_mes_aps_calendar_status', 'status'),
        {'comment': 'MES APS work calendars'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    calendar_code: Mapped[str] = mapped_column(sa.String(50))
    calendar_name: Mapped[str] = mapped_column(sa.String(100))
    weekday_mask: Mapped[str] = mapped_column(sa.String(20), default='1,2,3,4,5', server_default='1,2,3,4,5')
    timezone_name: Mapped[str] = mapped_column(sa.String(64), default='Asia/Hong_Kong', server_default='Asia/Hong_Kong')
    default_shift_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[ConfigStatus] = mapped_column(
        sa.String(20), default=ConfigStatus.ACTIVE, server_default=ConfigStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class CalendarDay(Base):
    """One date-specific work-calendar override."""

    __tablename__ = 'mes_aps_calendar_day'
    __table_args__ = (
        sa.ForeignKeyConstraint(['calendar_id'], ['mes_aps_calendar.id'], name='fk_aps_calendar_day_calendar'),
        sa.ForeignKeyConstraint(['shift_id'], ['mes_aps_shift.id'], name='fk_aps_calendar_day_shift'),
        sa.UniqueConstraint('calendar_id', 'work_date', 'deleted', name='uk_mes_aps_calendar_day_date'),
        sa.Index('idx_mes_aps_calendar_day_date', 'work_date'),
        {'comment': 'MES APS calendar date overrides'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    calendar_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_date: Mapped[date] = mapped_column(sa.Date())
    is_working_day: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    shift_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    capacity_factor: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('1'), server_default='1')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class WorkCenterCalendar(Base):
    """Effective-dated work-center calendar assignment."""

    __tablename__ = 'mes_aps_work_center_calendar'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_aps_center_calendar_center'),
        sa.ForeignKeyConstraint(['calendar_id'], ['mes_aps_calendar.id'], name='fk_aps_center_calendar_calendar'),
        sa.UniqueConstraint('work_center_id', 'effective_from', 'deleted', name='uk_mes_aps_center_calendar_effective'),
        sa.Index('idx_mes_aps_center_calendar_range', 'work_center_id', 'effective_from', 'effective_to'),
        {'comment': 'MES APS work-center calendar assignments'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    calendar_id: Mapped[int] = mapped_column(sa.BigInteger)
    effective_from: Mapped[date] = mapped_column(sa.Date())
    effective_to: Mapped[date | None] = mapped_column(sa.Date(), default=None)
    capacity_factor: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('1'), server_default='1')
    priority: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')


class ApsSchedule(Base):
    """One reproducible finite-capacity scheduling version."""

    __tablename__ = 'mes_aps_schedule'
    __table_args__ = (
        sa.UniqueConstraint('schedule_no', 'deleted', name='uk_mes_aps_schedule_no_deleted'),
        sa.Index('idx_mes_aps_schedule_status', 'status'),
        sa.Index('idx_mes_aps_schedule_horizon', 'horizon_start_at', 'horizon_end_at'),
        {'comment': 'MES APS finite-capacity schedule versions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    schedule_no: Mapped[str] = mapped_column(sa.String(100))
    schedule_name: Mapped[str] = mapped_column(sa.String(200))
    direction: Mapped[SchedulingDirection] = mapped_column(sa.String(20))
    horizon_start_at: Mapped[datetime] = mapped_column(TimeZone)
    horizon_end_at: Mapped[datetime] = mapped_column(TimeZone)
    started_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[ScheduleStatus] = mapped_column(
        sa.String(20), default=ScheduleStatus.RUNNING, server_default=ScheduleStatus.RUNNING.value
    )
    include_queue_time: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    include_move_time: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    work_order_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    operation_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    overdue_operation_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    error_message: Mapped[str | None] = mapped_column(UniversalText, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    published_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    published_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class ApsOperationSchedule(Base):
    """Scheduled work-order operation on one work-center capacity lane."""

    __tablename__ = 'mes_aps_operation_schedule'
    __table_args__ = (
        sa.ForeignKeyConstraint(['schedule_id'], ['mes_aps_schedule.id'], name='fk_aps_operation_schedule_header'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_aps_operation_schedule_order'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_aps_operation_schedule_wo_operation'),
        sa.ForeignKeyConstraint(['routing_operation_id'], ['mes_routing_operation.id'], name='fk_aps_operation_schedule_routing_operation'),
        sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_aps_operation_schedule_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_aps_operation_schedule_center'),
        sa.UniqueConstraint('schedule_id', 'work_order_operation_id', 'deleted', name='uk_mes_aps_schedule_wo_operation'),
        sa.Index('idx_mes_aps_operation_center_time', 'work_center_id', 'planned_start_at', 'planned_end_at'),
        sa.Index('idx_mes_aps_operation_order_sequence', 'work_order_id', 'sequence_no'),
        {'comment': 'MES APS operation schedule snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    schedule_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    sequence_no: Mapped[int] = mapped_column(sa.Integer)
    lane_no: Mapped[int] = mapped_column(sa.Integer)
    planned_start_at: Mapped[datetime] = mapped_column(TimeZone)
    planned_end_at: Mapped[datetime] = mapped_column(TimeZone)
    planned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    setup_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    run_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    queue_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    move_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    load_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    total_minutes: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4))
    work_order_no_snapshot: Mapped[str] = mapped_column(sa.String(100))
    product_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    product_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    operation_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    operation_name_snapshot: Mapped[str] = mapped_column(sa.String(150))
    work_center_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    work_center_name_snapshot: Mapped[str] = mapped_column(sa.String(150))
    routing_operation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[OperationScheduleStatus] = mapped_column(
        sa.String(20), default=OperationScheduleStatus.PLANNED, server_default=OperationScheduleStatus.PLANNED.value
    )
    is_overdue: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    dispatch_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')


class ApsDispatch(Base):
    """Dispatch instruction generated from one published scheduled operation."""

    __tablename__ = 'mes_aps_dispatch'
    __table_args__ = (
        sa.ForeignKeyConstraint(['schedule_operation_id'], ['mes_aps_operation_schedule.id'], name='fk_aps_dispatch_schedule_operation'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_aps_dispatch_order'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_aps_dispatch_wo_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_aps_dispatch_center'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['sys_user.id'], name='fk_aps_dispatch_assigned_user'),
        sa.ForeignKeyConstraint(['team_id'], ['mes_production_team.id'], name='fk_aps_dispatch_team'),
        sa.ForeignKeyConstraint(['workstation_id'], ['mes_workstation.id'], name='fk_aps_dispatch_workstation'),
        sa.ForeignKeyConstraint(['production_execution_id'], ['mes_production_execution.id'], name='fk_aps_dispatch_execution'),
        sa.UniqueConstraint('dispatch_no', 'deleted', name='uk_mes_aps_dispatch_no_deleted'),
        sa.Index('idx_mes_aps_dispatch_status', 'status'),
        sa.Index('idx_mes_aps_dispatch_center_time', 'work_center_id', 'planned_start_at'),
        sa.Index('idx_mes_aps_dispatch_team', 'team_id'),
        sa.Index('idx_mes_aps_dispatch_workstation', 'workstation_id'),
        sa.Index('idx_mes_aps_dispatch_execution', 'production_execution_id'),
        {'comment': 'MES APS shop-floor dispatch instructions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    dispatch_no: Mapped[str] = mapped_column(sa.String(100))
    schedule_operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    planned_start_at: Mapped[datetime] = mapped_column(TimeZone)
    planned_end_at: Mapped[datetime] = mapped_column(TimeZone)
    dispatch_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    priority: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    status: Mapped[DispatchStatus] = mapped_column(
        sa.String(20), default=DispatchStatus.DISPATCHED, server_default=DispatchStatus.DISPATCHED.value
    )
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    team_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    workstation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    production_execution_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    assigned_team: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    workstation_code: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    dispatched_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    dispatched_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    accepted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
