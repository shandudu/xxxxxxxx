from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.maintenance.enums import (
    CycleUnit,
    DowntimeCategory,
    DowntimeSourceType,
    DowntimeStatus,
    FaultLevel,
    MaintenancePlanType,
    PlanStatus,
    RepairStatus,
    TaskResult,
    TaskStatus,
)


class MaintenancePlan(Base):
    """Recurring equipment inspection or preventive-maintenance plan."""

    __tablename__ = 'mes_maintenance_plan'
    __table_args__ = (
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_maintenance_plan_equipment'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_maintenance_plan_center'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['sys_user.id'], name='fk_maintenance_plan_user'),
        sa.UniqueConstraint('plan_no', 'deleted', name='uk_mes_maintenance_plan_no_deleted'),
        sa.Index('idx_mes_maintenance_plan_due', 'status', 'next_due_date'),
        sa.Index('idx_mes_maintenance_plan_equipment', 'equipment_id'),
        {'comment': 'MES recurring inspection and preventive-maintenance plans'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    plan_no: Mapped[str] = mapped_column(sa.String(100))
    plan_name: Mapped[str] = mapped_column(sa.String(200))
    equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    plan_type: Mapped[MaintenancePlanType] = mapped_column(sa.String(30))
    cycle_unit: Mapped[CycleUnit] = mapped_column(sa.String(20))
    cycle_value: Mapped[int] = mapped_column(sa.Integer)
    next_due_date: Mapped[date] = mapped_column(sa.Date())
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lead_days: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    estimated_minutes: Mapped[int] = mapped_column(sa.Integer, default=30, server_default='30')
    requires_shutdown: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    checklist_json: Mapped[str | None] = mapped_column(UniversalText, default=None)
    status: Mapped[PlanStatus] = mapped_column(
        sa.String(20), default=PlanStatus.ACTIVE, server_default=PlanStatus.ACTIVE.value
    )
    last_generated_date: Mapped[date | None] = mapped_column(sa.Date(), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class EquipmentDowntime(Base):
    """Planned or unplanned equipment downtime that can block APS capacity."""

    __tablename__ = 'mes_equipment_downtime'
    __table_args__ = (
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_equipment_downtime_equipment'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_equipment_downtime_center'),
        sa.UniqueConstraint('downtime_no', 'deleted', name='uk_mes_equipment_downtime_no_deleted'),
        sa.Index('idx_mes_equipment_downtime_center_time', 'work_center_id', 'start_at', 'end_at'),
        sa.Index('idx_mes_equipment_downtime_status', 'status'),
        {'comment': 'MES equipment downtime intervals'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    downtime_no: Mapped[str] = mapped_column(sa.String(100))
    equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    category: Mapped[DowntimeCategory] = mapped_column(sa.String(20))
    source_type: Mapped[DowntimeSourceType] = mapped_column(sa.String(30))
    start_at: Mapped[datetime] = mapped_column(TimeZone)
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    end_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    status: Mapped[DowntimeStatus] = mapped_column(
        sa.String(20), default=DowntimeStatus.OPEN, server_default=DowntimeStatus.OPEN.value
    )
    affects_capacity: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    reason: Mapped[str | None] = mapped_column(UniversalText, default=None)
    duration_minutes: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 4), default=None)
    closed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class MaintenanceTask(Base):
    """Generated inspection or preventive-maintenance task."""

    __tablename__ = 'mes_maintenance_task'
    __table_args__ = (
        sa.ForeignKeyConstraint(['plan_id'], ['mes_maintenance_plan.id'], name='fk_maintenance_task_plan'),
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_maintenance_task_equipment'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_maintenance_task_center'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['sys_user.id'], name='fk_maintenance_task_user'),
        sa.ForeignKeyConstraint(['downtime_id'], ['mes_equipment_downtime.id'], name='fk_maintenance_task_downtime'),
        sa.UniqueConstraint('task_no', 'deleted', name='uk_mes_maintenance_task_no_deleted'),
        sa.UniqueConstraint('plan_id', 'due_date', 'deleted', name='uk_mes_maintenance_task_plan_due'),
        sa.Index('idx_mes_maintenance_task_status_due', 'status', 'due_date'),
        sa.Index('idx_mes_maintenance_task_equipment', 'equipment_id'),
        {'comment': 'MES generated inspection and maintenance tasks'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    task_no: Mapped[str] = mapped_column(sa.String(100))
    plan_id: Mapped[int] = mapped_column(sa.BigInteger)
    equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    task_type: Mapped[MaintenancePlanType] = mapped_column(sa.String(30))
    due_date: Mapped[date] = mapped_column(sa.Date())
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    estimated_minutes: Mapped[int] = mapped_column(sa.Integer, default=30, server_default='30')
    requires_shutdown: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    checklist_json: Mapped[str | None] = mapped_column(UniversalText, default=None)
    status: Mapped[TaskStatus] = mapped_column(
        sa.String(20), default=TaskStatus.PENDING, server_default=TaskStatus.PENDING.value
    )
    result: Mapped[TaskResult | None] = mapped_column(sa.String(20), default=None)
    checklist_result_json: Mapped[str | None] = mapped_column(UniversalText, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    downtime_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    findings: Mapped[str | None] = mapped_column(UniversalText, default=None)
    action_taken: Mapped[str | None] = mapped_column(UniversalText, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class RepairOrder(Base):
    """Corrective equipment repair order."""

    __tablename__ = 'mes_repair_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_repair_order_equipment'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_repair_order_center'),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['sys_user.id'], name='fk_repair_order_user'),
        sa.ForeignKeyConstraint(['downtime_id'], ['mes_equipment_downtime.id'], name='fk_repair_order_downtime'),
        sa.UniqueConstraint('repair_no', 'deleted', name='uk_mes_repair_order_no_deleted'),
        sa.Index('idx_mes_repair_order_status', 'status'),
        sa.Index('idx_mes_repair_order_equipment', 'equipment_id'),
        sa.Index('idx_mes_repair_order_reported', 'reported_at'),
        {'comment': 'MES corrective equipment repair orders'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    repair_no: Mapped[str] = mapped_column(sa.String(100))
    equipment_id: Mapped[int] = mapped_column(sa.BigInteger)
    fault_level: Mapped[FaultLevel] = mapped_column(sa.String(20))
    fault_description: Mapped[str] = mapped_column(UniversalText)
    reported_at: Mapped[datetime] = mapped_column(TimeZone)
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    assigned_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[RepairStatus] = mapped_column(
        sa.String(20), default=RepairStatus.REPORTED, server_default=RepairStatus.REPORTED.value
    )
    affects_capacity: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    downtime_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reported_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    root_cause: Mapped[str | None] = mapped_column(UniversalText, default=None)
    repair_action: Mapped[str | None] = mapped_column(UniversalText, default=None)
    spare_parts_used: Mapped[str | None] = mapped_column(UniversalText, default=None)
    repair_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class RepairPartIssue(Base):
    """Spare-part issue posted to inventory for a repair order."""

    __tablename__ = 'mes_repair_part_issue'
    __table_args__ = (
        sa.ForeignKeyConstraint(['repair_id'], ['mes_repair_order.id'], name='fk_repair_part_issue_repair'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_repair_part_issue_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_repair_part_issue_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_repair_part_issue_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_repair_part_issue_location'),
        sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_repair_part_issue_idempotency'),
        sa.Index('idx_repair_part_issue_repair', 'repair_id', 'issued_at'),
        {'comment': 'MES repair spare-part issues linked to inventory transactions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    repair_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    idempotency_key: Mapped[str] = mapped_column(sa.String(180))
    issued_at: Mapped[datetime] = mapped_column(TimeZone)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    unit_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    total_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    stock_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class RepairCostPosting(Base):
    """Posted repair cost summary and its GL voucher."""

    __tablename__ = 'mes_repair_cost_posting'
    __table_args__ = (
        sa.ForeignKeyConstraint(['repair_id'], ['mes_repair_order.id'], name='fk_repair_cost_posting_repair'),
        sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_repair_cost_posting_period'),
        sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_repair_cost_posting_voucher'),
        sa.UniqueConstraint('repair_id', 'deleted', name='uk_repair_cost_posting_repair'),
        sa.Index('idx_repair_cost_posting_period', 'period_id', 'posted_at'),
        {'comment': 'MES repair cost posting to general ledger'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    repair_id: Mapped[int] = mapped_column(sa.BigInteger)
    period_id: Mapped[int] = mapped_column(sa.BigInteger)
    posted_at: Mapped[datetime] = mapped_column(TimeZone)
    parts_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    labor_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    total_cost: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    voucher_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
