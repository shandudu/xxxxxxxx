from __future__ import annotations

import calendar as month_calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.app.admin.model.user import User
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.equipment.enums import EquipmentStatus
from backend.plugin.equipment.model import Equipment
from backend.plugin.maintenance.crud import maintenance_repository
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
from backend.plugin.maintenance.model import (
    EquipmentDowntime,
    MaintenancePlan,
    MaintenanceTask,
    RepairOrder,
    RepairPartIssue,
    RepairCostPosting,
)
from backend.plugin.maintenance.schema.maintenance import (
    AssignRepair,
    CloseDowntime,
    CompleteRepair,
    CompleteTask,
    CreateDowntime,
    CreateMaintenancePlan,
    CreateRepairOrder,
    DowntimeDetail,
    GenerateDueTasks,
    MaintenanceDashboard,
    MaintenancePlanDetail,
    MaintenanceTaskDetail,
    RepairOrderDetail,
    IssueRepairPart,
    RepairPartIssueDetail,
    PostRepairCost,
    RepairCostPostingDetail,
    RepairCostAnalysisRow,
    RepairCostAnalysisSummary,
    StartRepair,
    StartTask,
    UpdateMaintenancePlan,
)
from backend.plugin.routing.enums import WorkCenterStatus
from backend.plugin.routing.model import WorkCenter
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.service import inventory_service
from backend.plugin.finance.enums import FinancePeriodStatus, VoucherStatus
from backend.plugin.finance.model import FinancePeriod, GLVoucher, GLVoucherLine
from backend.utils.timezone import timezone


def advance_cycle(value: date, unit: CycleUnit, amount: int) -> date:
    if unit == CycleUnit.DAY:
        return value + timedelta(days=amount)
    if unit == CycleUnit.WEEK:
        return value + timedelta(weeks=amount)
    month_index = value.month - 1 + amount
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, month_calendar.monthrange(year, month)[1])
    return date(year, month, day)


def duration_minutes(start_at: datetime, end_at: datetime) -> Decimal:
    return (Decimal(str((end_at - start_at).total_seconds())) / Decimal('60')).quantize(
        Decimal('0.0001'), rounding=ROUND_HALF_UP
    )


def parse_json_list(value: str | None) -> list:
    if not value:
        return []


def enum_value(value: object) -> str:
    """Return one stable value for both StrEnum instances and DB-loaded strings."""
    return str(getattr(value, 'value', value))


def is_due_for_generation(next_due_date: date, lead_days: int, through_date: date) -> bool:
    """A plan is eligible when its generation date falls on or before the requested date."""
    return next_due_date - timedelta(days=lead_days) <= through_date
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


class MaintenanceService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _equipment(
        db: AsyncSession,
        equipment_id: int,
        *,
        require_maintenance_enabled: bool = True,
    ) -> Equipment:
        row = await db.scalar(
            select(Equipment).where(Equipment.id == equipment_id, Equipment.deleted == 0)
        )
        if not row:
            raise errors.NotFoundError(msg='EQUIPMENT_NOT_FOUND')
        if require_maintenance_enabled and (not row.enabled or not row.maintenance_enabled):
            raise errors.ConflictError(msg='EQUIPMENT_MAINTENANCE_DISABLED')
        return row

    @staticmethod
    async def _center(db: AsyncSession, work_center_id: int | None) -> WorkCenter | None:
        if work_center_id is None:
            return None
        row = await db.scalar(
            select(WorkCenter).where(WorkCenter.id == work_center_id, WorkCenter.deleted == 0)
        )
        if not row:
            raise errors.NotFoundError(msg='WORK_CENTER_NOT_FOUND')
        if row.status != WorkCenterStatus.ACTIVE:
            raise errors.ConflictError(msg='WORK_CENTER_DISABLED')
        return row

    @staticmethod
    async def _user(db: AsyncSession, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        row = await db.scalar(
            select(User).where(User.id == user_id, User.deleted == 0, User.status == 1)
        )
        if not row:
            raise errors.NotFoundError(msg='ASSIGNED_USER_NOT_FOUND')
        return row

    @staticmethod
    async def _plan(db: AsyncSession, plan_id: int, *, lock: bool = False) -> MaintenancePlan:
        stmt = select(MaintenancePlan).where(
            MaintenancePlan.id == plan_id, MaintenancePlan.deleted == 0
        )
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='MAINTENANCE_PLAN_NOT_FOUND')
        return row

    @staticmethod
    async def _task(db: AsyncSession, task_id: int, *, lock: bool = False) -> MaintenanceTask:
        stmt = select(MaintenanceTask).where(
            MaintenanceTask.id == task_id, MaintenanceTask.deleted == 0
        )
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='MAINTENANCE_TASK_NOT_FOUND')
        return row

    @staticmethod
    async def _repair(db: AsyncSession, repair_id: int, *, lock: bool = False) -> RepairOrder:
        stmt = select(RepairOrder).where(RepairOrder.id == repair_id, RepairOrder.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='REPAIR_ORDER_NOT_FOUND')
        return row

    @staticmethod
    async def _downtime(
        db: AsyncSession, downtime_id: int, *, lock: bool = False
    ) -> EquipmentDowntime:
        stmt = select(EquipmentDowntime).where(
            EquipmentDowntime.id == downtime_id, EquipmentDowntime.deleted == 0
        )
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='EQUIPMENT_DOWNTIME_NOT_FOUND')
        return row

    @staticmethod
    async def _plan_detail(db: AsyncSession, plan: MaintenancePlan) -> MaintenancePlanDetail:
        equipment = await db.scalar(select(Equipment).where(Equipment.id == plan.equipment_id))
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == plan.work_center_id)) if plan.work_center_id else None
        user = await db.scalar(select(User).where(User.id == plan.assigned_user_id)) if plan.assigned_user_id else None
        result = MaintenancePlanDetail.model_validate(plan)
        result.equipment_code = equipment.equipment_code if equipment else ''
        result.equipment_name = equipment.equipment_name if equipment else ''
        result.work_center_name = center.work_center_name if center else None
        result.assigned_username = user.username if user else None
        result.checklist_items = parse_json_list(plan.checklist_json)
        return result

    @staticmethod
    async def _task_detail(db: AsyncSession, task: MaintenanceTask) -> MaintenanceTaskDetail:
        plan = await db.scalar(select(MaintenancePlan).where(MaintenancePlan.id == task.plan_id))
        equipment = await db.scalar(select(Equipment).where(Equipment.id == task.equipment_id))
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == task.work_center_id)) if task.work_center_id else None
        user = await db.scalar(select(User).where(User.id == task.assigned_user_id)) if task.assigned_user_id else None
        result = MaintenanceTaskDetail.model_validate(task)
        result.plan_name = plan.plan_name if plan else ''
        result.equipment_code = equipment.equipment_code if equipment else ''
        result.equipment_name = equipment.equipment_name if equipment else ''
        result.work_center_name = center.work_center_name if center else None
        result.assigned_username = user.username if user else None
        result.checklist_items = parse_json_list(task.checklist_json)
        result.checklist_results = parse_json_list(task.checklist_result_json)
        result.overdue = task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS) and task.due_date < timezone.now().date()
        return result

    @staticmethod
    async def _repair_detail(db: AsyncSession, repair: RepairOrder) -> RepairOrderDetail:
        equipment = await db.scalar(select(Equipment).where(Equipment.id == repair.equipment_id))
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == repair.work_center_id)) if repair.work_center_id else None
        user = await db.scalar(select(User).where(User.id == repair.assigned_user_id)) if repair.assigned_user_id else None
        result = RepairOrderDetail.model_validate(repair)
        result.equipment_code = equipment.equipment_code if equipment else ''
        result.equipment_name = equipment.equipment_name if equipment else ''
        result.work_center_name = center.work_center_name if center else None
        result.assigned_username = user.username if user else None
        return result

    @staticmethod
    async def _downtime_detail(db: AsyncSession, downtime: EquipmentDowntime) -> DowntimeDetail:
        equipment = await db.scalar(select(Equipment).where(Equipment.id == downtime.equipment_id))
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == downtime.work_center_id)) if downtime.work_center_id else None
        result = DowntimeDetail.model_validate(downtime)
        result.equipment_code = equipment.equipment_code if equipment else ''
        result.equipment_name = equipment.equipment_name if equipment else ''
        result.work_center_name = center.work_center_name if center else None
        return result

    @staticmethod
    async def list_plans(db: AsyncSession) -> list[MaintenancePlanDetail]:
        return [await MaintenanceService._plan_detail(db, row) for row in await maintenance_repository.plans(db)]

    @staticmethod
    async def create_plan(db: AsyncSession, obj: CreateMaintenancePlan) -> MaintenancePlanDetail:
        await MaintenanceService._equipment(db, obj.equipment_id)
        await MaintenanceService._center(db, obj.work_center_id)
        await MaintenanceService._user(db, obj.assigned_user_id)
        plan_no = obj.plan_no or f'MP-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'
        if await db.scalar(select(MaintenancePlan.id).where(MaintenancePlan.plan_no == plan_no, MaintenancePlan.deleted == 0)):
            raise errors.ConflictError(msg='MAINTENANCE_PLAN_NO_EXISTS')
        data = obj.model_dump(exclude={'checklist_items', 'plan_no'})
        row = MaintenancePlan(
            plan_no=plan_no,
            checklist_json=json.dumps(obj.checklist_items, ensure_ascii=False),
            **data,
        )
        row.created_by = MaintenanceService._operator_id()
        db.add(row)
        await db.flush()
        return await MaintenanceService._plan_detail(db, row)

    @staticmethod
    async def update_plan(db: AsyncSession, plan_id: int, obj: UpdateMaintenancePlan) -> MaintenancePlanDetail:
        row = await MaintenanceService._plan(db, plan_id, lock=True)
        await MaintenanceService._equipment(db, obj.equipment_id)
        await MaintenanceService._center(db, obj.work_center_id)
        await MaintenanceService._user(db, obj.assigned_user_id)
        requested_no = obj.plan_no or row.plan_no
        duplicate = await db.scalar(select(MaintenancePlan.id).where(MaintenancePlan.plan_no == requested_no, MaintenancePlan.id != plan_id, MaintenancePlan.deleted == 0))
        if duplicate:
            raise errors.ConflictError(msg='MAINTENANCE_PLAN_NO_EXISTS')
        data = obj.model_dump(exclude={'checklist_items', 'plan_no'})
        for key, value in data.items():
            setattr(row, key, value)
        row.plan_no = requested_no
        row.checklist_json = json.dumps(obj.checklist_items, ensure_ascii=False)
        row.updated_by = MaintenanceService._operator_id()
        await db.flush()
        return await MaintenanceService._plan_detail(db, row)

    @staticmethod
    async def generate_due_tasks(db: AsyncSession, obj: GenerateDueTasks) -> list[MaintenanceTaskDetail]:
        plans = list(
            (
                await db.scalars(
                    select(MaintenancePlan)
                    .where(
                        MaintenancePlan.deleted == 0,
                        MaintenancePlan.status == PlanStatus.ACTIVE,
                        # lead_days is validated to at most 365; this portable upper bound
                        # avoids scanning plans that cannot yet become eligible.
                        MaintenancePlan.next_due_date <= obj.through_date + timedelta(days=365),
                    )
                    .order_by(MaintenancePlan.next_due_date)
                    .with_for_update()
                )
            ).all()
        )
        generated: list[MaintenanceTask] = []
        for plan in plans:
            while (
                is_due_for_generation(plan.next_due_date, plan.lead_days, obj.through_date)
                and len(generated) < obj.max_tasks
            ):
                due_date = plan.next_due_date
                existing = await db.scalar(select(MaintenanceTask.id).where(MaintenanceTask.plan_id == plan.id, MaintenanceTask.due_date == due_date, MaintenanceTask.deleted == 0))
                if not existing:
                    task = MaintenanceTask(
                        task_no=f'MT-{due_date:%Y%m%d}-{uuid4().hex[:8]}'.upper(),
                        plan_id=plan.id,
                        equipment_id=plan.equipment_id,
                        task_type=plan.plan_type,
                        due_date=due_date,
                        work_center_id=plan.work_center_id,
                        assigned_user_id=plan.assigned_user_id,
                        estimated_minutes=plan.estimated_minutes,
                        requires_shutdown=plan.requires_shutdown,
                        checklist_json=plan.checklist_json,
                    )
                    task.created_by = MaintenanceService._operator_id()
                    db.add(task)
                    generated.append(task)
                plan.last_generated_date = due_date
                plan.next_due_date = advance_cycle(due_date, plan.cycle_unit, plan.cycle_value)
            if len(generated) >= obj.max_tasks:
                break
        await db.flush()
        return [await MaintenanceService._task_detail(db, row) for row in generated]

    @staticmethod
    async def list_tasks(db: AsyncSession) -> list[MaintenanceTaskDetail]:
        return [await MaintenanceService._task_detail(db, row) for row in await maintenance_repository.tasks(db)]

    @staticmethod
    async def _open_downtime(
        db: AsyncSession,
        *,
        equipment_id: int,
        work_center_id: int | None,
        category: DowntimeCategory,
        source_type: DowntimeSourceType,
        source_id: int | None,
        start_at: datetime,
        affects_capacity: bool,
        reason: str | None,
    ) -> EquipmentDowntime:
        row = EquipmentDowntime(
            downtime_no=f'DT-{start_at:%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            equipment_id=equipment_id,
            work_center_id=work_center_id,
            category=category,
            source_type=source_type,
            source_id=source_id,
            start_at=start_at,
            affects_capacity=affects_capacity,
            reason=reason,
        )
        row.created_by = MaintenanceService._operator_id()
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def _close_downtime_row(db: AsyncSession, row: EquipmentDowntime, end_at: datetime, remark: str | None = None) -> None:
        if end_at <= row.start_at:
            raise errors.ConflictError(msg='DOWNTIME_END_MUST_BE_AFTER_START')
        row.end_at = end_at
        row.duration_minutes = duration_minutes(row.start_at, end_at)
        row.status = DowntimeStatus.CLOSED
        row.closed_by = MaintenanceService._operator_id()
        row.remark = remark or row.remark
        await db.flush()

    @staticmethod
    async def start_task(db: AsyncSession, task_id: int, obj: StartTask) -> MaintenanceTaskDetail:
        task = await MaintenanceService._task(db, task_id, lock=True)
        if task.status != TaskStatus.PENDING:
            raise errors.ConflictError(msg='MAINTENANCE_TASK_NOT_STARTABLE')
        equipment = await MaintenanceService._equipment(db, task.equipment_id)
        now = obj.started_at or timezone.now()
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = now
        if task.requires_shutdown:
            source_type = DowntimeSourceType.INSPECTION if task.task_type == MaintenancePlanType.INSPECTION else DowntimeSourceType.MAINTENANCE
            downtime = await MaintenanceService._open_downtime(
                db,
                equipment_id=task.equipment_id,
                work_center_id=task.work_center_id,
                category=DowntimeCategory.PLANNED,
                source_type=source_type,
                source_id=task.id,
                start_at=now,
                affects_capacity=True,
                reason=f'{enum_value(task.task_type)} {task.task_no}',
            )
            task.downtime_id = downtime.id
            equipment.status = EquipmentStatus.MAINTENANCE
        await db.flush()
        return await MaintenanceService._task_detail(db, task)

    @staticmethod
    async def _restore_equipment_status(db: AsyncSession, equipment: Equipment) -> None:
        if not equipment.enabled:
            equipment.status = EquipmentStatus.DISABLED
            return
        open_categories = {
            enum_value(category)
            for category in (
                await db.scalars(
                    select(EquipmentDowntime.category).where(
                        EquipmentDowntime.equipment_id == equipment.id,
                        EquipmentDowntime.status == DowntimeStatus.OPEN,
                        EquipmentDowntime.deleted == 0,
                    )
                )
            ).all()
        }
        if DowntimeCategory.UNPLANNED.value in open_categories:
            equipment.status = EquipmentStatus.DOWN
        elif open_categories:
            equipment.status = EquipmentStatus.MAINTENANCE
        else:
            equipment.status = EquipmentStatus.IDLE

    @staticmethod
    async def complete_task(db: AsyncSession, task_id: int, obj: CompleteTask) -> MaintenanceTaskDetail:
        task = await MaintenanceService._task(db, task_id, lock=True)
        if task.status != TaskStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='MAINTENANCE_TASK_NOT_COMPLETABLE')
        completed_at = obj.completed_at or timezone.now()
        if task.started_at and completed_at < task.started_at:
            raise errors.ConflictError(msg='TASK_COMPLETION_BEFORE_START')
        task.status = TaskStatus.COMPLETED
        task.result = obj.result
        task.checklist_result_json = json.dumps(obj.checklist_results, ensure_ascii=False)
        task.findings = obj.findings
        task.action_taken = obj.action_taken
        task.completed_at = completed_at
        task.remark = obj.remark
        if task.downtime_id:
            downtime = await MaintenanceService._downtime(db, task.downtime_id, lock=True)
            if downtime.status == DowntimeStatus.OPEN:
                await MaintenanceService._close_downtime_row(db, downtime, completed_at)
        equipment = await MaintenanceService._equipment(
            db, task.equipment_id, require_maintenance_enabled=False
        )
        await MaintenanceService._restore_equipment_status(db, equipment)
        await db.flush()
        if obj.result == TaskResult.FAIL and obj.create_repair_on_fail:
            await MaintenanceService.create_repair(
                db,
                CreateRepairOrder(
                    equipment_id=task.equipment_id,
                    work_center_id=task.work_center_id,
                    fault_level=FaultLevel.MAJOR,
                    fault_description=obj.findings or f'Task {task.task_no} failed',
                    assigned_user_id=task.assigned_user_id,
                    affects_capacity=True,
                    reported_at=completed_at,
                    remark=f'Automatically created from maintenance task {task.task_no}',
                ),
            )
        return await MaintenanceService._task_detail(db, task)

    @staticmethod
    async def list_repairs(db: AsyncSession) -> list[RepairOrderDetail]:
        return [await MaintenanceService._repair_detail(db, row) for row in await maintenance_repository.repairs(db)]

    @staticmethod
    async def create_repair(db: AsyncSession, obj: CreateRepairOrder) -> RepairOrderDetail:
        equipment = await MaintenanceService._equipment(db, obj.equipment_id)
        await MaintenanceService._center(db, obj.work_center_id)
        await MaintenanceService._user(db, obj.assigned_user_id)
        now = obj.reported_at or timezone.now()
        repair_no = obj.repair_no or f'RP-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6]}'
        if await db.scalar(select(RepairOrder.id).where(RepairOrder.repair_no == repair_no, RepairOrder.deleted == 0)):
            raise errors.ConflictError(msg='REPAIR_ORDER_NO_EXISTS')
        row = RepairOrder(
            repair_no=repair_no,
            equipment_id=obj.equipment_id,
            work_center_id=obj.work_center_id,
            fault_level=obj.fault_level,
            fault_description=obj.fault_description,
            reported_at=now,
            assigned_user_id=obj.assigned_user_id,
            status=RepairStatus.ASSIGNED if obj.assigned_user_id else RepairStatus.REPORTED,
            affects_capacity=obj.affects_capacity,
            reported_by=MaintenanceService._operator_id(),
            remark=obj.remark,
        )
        row.created_by = MaintenanceService._operator_id()
        db.add(row)
        await db.flush()
        if obj.affects_capacity:
            downtime = await MaintenanceService._open_downtime(
                db,
                equipment_id=row.equipment_id,
                work_center_id=row.work_center_id,
                category=DowntimeCategory.UNPLANNED,
                source_type=DowntimeSourceType.REPAIR,
                source_id=row.id,
                start_at=now,
                affects_capacity=True,
                reason=row.fault_description,
            )
            row.downtime_id = downtime.id
            equipment.status = EquipmentStatus.DOWN
        await db.flush()
        return await MaintenanceService._repair_detail(db, row)

    @staticmethod
    async def assign_repair(db: AsyncSession, repair_id: int, obj: AssignRepair) -> RepairOrderDetail:
        row = await MaintenanceService._repair(db, repair_id, lock=True)
        if row.status not in (RepairStatus.REPORTED, RepairStatus.ASSIGNED):
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_ASSIGNABLE')
        await MaintenanceService._user(db, obj.assigned_user_id)
        row.assigned_user_id = obj.assigned_user_id
        row.status = RepairStatus.ASSIGNED
        await db.flush()
        return await MaintenanceService._repair_detail(db, row)

    @staticmethod
    async def start_repair(db: AsyncSession, repair_id: int, obj: StartRepair) -> RepairOrderDetail:
        row = await MaintenanceService._repair(db, repair_id, lock=True)
        if row.status not in (RepairStatus.REPORTED, RepairStatus.ASSIGNED):
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_STARTABLE')
        equipment = await MaintenanceService._equipment(db, row.equipment_id)
        now = obj.started_at or timezone.now()
        row.status = RepairStatus.IN_REPAIR
        row.started_at = now
        equipment.status = EquipmentStatus.MAINTENANCE
        if row.affects_capacity and not row.downtime_id:
            downtime = await MaintenanceService._open_downtime(
                db,
                equipment_id=row.equipment_id,
                work_center_id=row.work_center_id,
                category=DowntimeCategory.UNPLANNED,
                source_type=DowntimeSourceType.REPAIR,
                source_id=row.id,
                start_at=now,
                affects_capacity=True,
                reason=row.fault_description,
            )
            row.downtime_id = downtime.id
        await db.flush()
        return await MaintenanceService._repair_detail(db, row)

    @staticmethod
    async def complete_repair(db: AsyncSession, repair_id: int, obj: CompleteRepair) -> RepairOrderDetail:
        row = await MaintenanceService._repair(db, repair_id, lock=True)
        if row.status != RepairStatus.IN_REPAIR:
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_COMPLETABLE')
        completed_at = obj.completed_at or timezone.now()
        if row.started_at and completed_at < row.started_at:
            raise errors.ConflictError(msg='REPAIR_COMPLETION_BEFORE_START')
        row.status = RepairStatus.COMPLETED
        row.completed_at = completed_at
        row.root_cause = obj.root_cause
        row.repair_action = obj.repair_action
        row.spare_parts_used = obj.spare_parts_used
        row.repair_cost = obj.repair_cost
        row.remark = obj.remark or row.remark
        if row.downtime_id:
            downtime = await MaintenanceService._downtime(db, row.downtime_id, lock=True)
            if downtime.status == DowntimeStatus.OPEN:
                await MaintenanceService._close_downtime_row(db, downtime, completed_at)
        equipment = await MaintenanceService._equipment(
            db, row.equipment_id, require_maintenance_enabled=False
        )
        await MaintenanceService._restore_equipment_status(db, equipment)
        await db.flush()
        return await MaintenanceService._repair_detail(db, row)

    @staticmethod
    async def list_repair_parts(db: AsyncSession, repair_id: int) -> list[RepairPartIssueDetail]:
        await MaintenanceService._repair(db, repair_id)
        rows = (await db.scalars(select(RepairPartIssue).where(RepairPartIssue.repair_id == repair_id, RepairPartIssue.deleted == 0).order_by(RepairPartIssue.id))).all()
        return [RepairPartIssueDetail.model_validate(row) for row in rows]

    @staticmethod
    async def issue_repair_part(db: AsyncSession, repair_id: int, obj: IssueRepairPart) -> RepairPartIssueDetail:
        repair = await MaintenanceService._repair(db, repair_id, lock=True)
        if repair.status not in (RepairStatus.IN_REPAIR, RepairStatus.COMPLETED):
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_ISSUEABLE')
        posting = await db.scalar(
            select(RepairCostPosting.id).where(
                RepairCostPosting.repair_id == repair.id,
                RepairCostPosting.deleted == 0,
            )
        )
        if posting:
            raise errors.ConflictError(msg='REPAIR_COST_ALREADY_POSTED')
        existing = await db.scalar(
            select(RepairPartIssue).where(
                RepairPartIssue.repair_id == repair.id,
                RepairPartIssue.idempotency_key == obj.idempotency_key,
                RepairPartIssue.deleted == 0,
            )
        )
        if existing:
            same_request = (
                existing.material_id == obj.material_id
                and existing.lot_id == obj.lot_id
                and existing.warehouse_id == obj.warehouse_id
                and existing.location_id == obj.location_id
                and existing.quantity == obj.quantity
                and existing.unit_cost == obj.unit_cost
            )
            if not same_request:
                raise errors.ConflictError(msg='REPAIR_PART_IDEMPOTENCY_CONFLICT')
            return RepairPartIssueDetail.model_validate(existing)
        issued_at = obj.issued_at or timezone.now()
        issue = RepairPartIssue(
            repair_id=repair.id, material_id=obj.material_id, lot_id=obj.lot_id,
            warehouse_id=obj.warehouse_id, location_id=obj.location_id, quantity=obj.quantity,
            unit_cost=obj.unit_cost, total_cost=(obj.quantity * obj.unit_cost).quantize(Decimal('0.000001')),
            idempotency_key=obj.idempotency_key, issued_at=issued_at, remark=obj.remark,
        )
        db.add(issue)
        await db.flush()
        transaction = await inventory_service.post_transaction(
            db, idempotency_key=f'REPAIR_PART:{repair.id}:{obj.idempotency_key}', transaction_type=StockTransactionType.ISSUE,
            material_id=obj.material_id, lot_id=obj.lot_id, warehouse_id=obj.warehouse_id,
            location_id=obj.location_id, quantity_delta=-obj.quantity, reference_type='REPAIR_ORDER',
            reference_id=repair.id, reference_no=repair.repair_no, remark=obj.remark,
            operator_id=MaintenanceService._operator_id(),
        )
        issue.stock_transaction_id = transaction.id
        await db.flush()
        return RepairPartIssueDetail.model_validate(issue)

    @staticmethod
    async def post_repair_cost(db: AsyncSession, repair_id: int, obj: PostRepairCost) -> RepairCostPostingDetail:
        repair = await MaintenanceService._repair(db, repair_id, lock=True)
        if repair.status != RepairStatus.COMPLETED:
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_COST_POSTABLE')
        existing = await db.scalar(select(RepairCostPosting).where(RepairCostPosting.repair_id == repair_id, RepairCostPosting.deleted == 0))
        if existing:
            return RepairCostPostingDetail.model_validate(existing)
        period = await db.scalar(select(FinancePeriod).where(FinancePeriod.id == obj.period_id, FinancePeriod.deleted == 0))
        if not period:
            raise errors.NotFoundError(msg='FINANCE_PERIOD_NOT_FOUND')
        if period.status != FinancePeriodStatus.OPEN:
            raise errors.ConflictError(msg='FINANCE_PERIOD_CLOSED')
        parts_cost = Decimal(await db.scalar(select(func.coalesce(func.sum(RepairPartIssue.total_cost), 0)).where(RepairPartIssue.repair_id == repair_id, RepairPartIssue.deleted == 0)) or 0)
        total = (parts_cost + obj.labor_cost).quantize(Decimal('0.000001'))
        if total <= 0:
            raise errors.RequestError(msg='REPAIR_COST_MUST_BE_POSITIVE')
        now = timezone.now()
        posting = RepairCostPosting(repair_id=repair_id, period_id=obj.period_id, parts_cost=parts_cost, labor_cost=obj.labor_cost, total_cost=total, posted_at=now, remark=obj.remark)
        db.add(posting)
        await db.flush()
        voucher = GLVoucher(voucher_no=f'V-REPAIR-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}', period_id=obj.period_id, voucher_date=now.date(), source_type='REPAIR_COST', source_id=posting.id, summary=f'维修费用 {repair.repair_no}', total_debit=total, total_credit=total, status=VoucherStatus.POSTED, posted_at=now)
        db.add(voucher)
        await db.flush()
        db.add_all([
            GLVoucherLine(voucher_id=voucher.id, line_no=1, account_code='6602', account_name='维修费用', debit=total, credit=Decimal('0'), description=repair.repair_no),
            GLVoucherLine(voucher_id=voucher.id, line_no=2, account_code='2202', account_name='应付账款', debit=Decimal('0'), credit=total, description=repair.repair_no),
        ])
        posting.voucher_id = voucher.id
        repair.repair_cost = total
        await db.flush()
        return RepairCostPostingDetail.model_validate(posting)

    @staticmethod
    async def repair_cost_analysis(db: AsyncSession, period_id: int | None = None, hourly_downtime_cost: Decimal = Decimal('0')) -> RepairCostAnalysisSummary:
        query = select(RepairCostPosting, RepairOrder, Equipment).join(RepairOrder, RepairOrder.id == RepairCostPosting.repair_id).join(Equipment, Equipment.id == RepairOrder.equipment_id).where(RepairCostPosting.deleted == 0, RepairOrder.deleted == 0)
        if period_id is not None:
            query = query.where(RepairCostPosting.period_id == period_id)
        rows = (await db.execute(query.order_by(RepairCostPosting.posted_at.desc()))).all()
        result_rows: list[RepairCostAnalysisRow] = []
        total_parts = total_labor = total_repair = total_minutes = total_downtime_cost = Decimal('0')
        for posting, repair, equipment in rows:
            minutes = Decimal('0')
            if repair.downtime_id:
                downtime = await db.scalar(select(EquipmentDowntime).where(EquipmentDowntime.id == repair.downtime_id, EquipmentDowntime.deleted == 0))
                if downtime:
                    minutes = downtime.duration_minutes or duration_minutes(downtime.start_at, timezone.now())
            downtime_cost = (minutes / Decimal('60') * hourly_downtime_cost).quantize(Decimal('0.000001'))
            result_rows.append(RepairCostAnalysisRow(repair_id=repair.id, repair_no=repair.repair_no, equipment_id=equipment.id, equipment_code=equipment.equipment_code, equipment_name=equipment.equipment_name, repair_status=repair.status, parts_cost=posting.parts_cost, labor_cost=posting.labor_cost, total_cost=posting.total_cost, downtime_minutes=minutes, downtime_cost=downtime_cost))
            total_parts += posting.parts_cost; total_labor += posting.labor_cost; total_repair += posting.total_cost; total_minutes += minutes; total_downtime_cost += downtime_cost
        return RepairCostAnalysisSummary(period_id=period_id, hourly_downtime_cost=hourly_downtime_cost, repair_count=len(result_rows), downtime_minutes=total_minutes, downtime_cost=total_downtime_cost, total_parts_cost=total_parts, total_labor_cost=total_labor, total_repair_cost=total_repair, rows=result_rows)

    @staticmethod
    async def cancel_repair(db: AsyncSession, repair_id: int) -> RepairOrderDetail:
        row = await MaintenanceService._repair(db, repair_id, lock=True)
        if row.status in (RepairStatus.COMPLETED, RepairStatus.CANCELLED):
            raise errors.ConflictError(msg='REPAIR_ORDER_NOT_CANCELLABLE')
        row.status = RepairStatus.CANCELLED
        now = timezone.now()
        if row.downtime_id:
            downtime = await MaintenanceService._downtime(db, row.downtime_id, lock=True)
            if downtime.status == DowntimeStatus.OPEN:
                await MaintenanceService._close_downtime_row(db, downtime, now, 'Repair cancelled')
        equipment = await MaintenanceService._equipment(
            db, row.equipment_id, require_maintenance_enabled=False
        )
        await MaintenanceService._restore_equipment_status(db, equipment)
        await db.flush()
        return await MaintenanceService._repair_detail(db, row)

    @staticmethod
    async def list_downtimes(db: AsyncSession) -> list[DowntimeDetail]:
        return [await MaintenanceService._downtime_detail(db, row) for row in await maintenance_repository.downtimes(db)]

    @staticmethod
    async def create_downtime(db: AsyncSession, obj: CreateDowntime) -> DowntimeDetail:
        equipment = await MaintenanceService._equipment(db, obj.equipment_id)
        await MaintenanceService._center(db, obj.work_center_id)
        downtime_no = obj.downtime_no or f'DT-{obj.start_at:%Y%m%d%H%M%S}-{uuid4().hex[:6]}'
        if await db.scalar(select(EquipmentDowntime.id).where(EquipmentDowntime.downtime_no == downtime_no, EquipmentDowntime.deleted == 0)):
            raise errors.ConflictError(msg='DOWNTIME_NO_EXISTS')
        row = EquipmentDowntime(
            downtime_no=downtime_no,
            equipment_id=obj.equipment_id,
            work_center_id=obj.work_center_id,
            category=obj.category,
            source_type=obj.source_type,
            source_id=obj.source_id,
            start_at=obj.start_at,
            end_at=obj.end_at,
            status=DowntimeStatus.CLOSED if obj.end_at else DowntimeStatus.OPEN,
            affects_capacity=obj.affects_capacity,
            reason=obj.reason,
            duration_minutes=duration_minutes(obj.start_at, obj.end_at) if obj.end_at else None,
            remark=obj.remark,
        )
        row.created_by = MaintenanceService._operator_id()
        db.add(row)
        if row.status == DowntimeStatus.OPEN:
            equipment.status = EquipmentStatus.DOWN if obj.category == DowntimeCategory.UNPLANNED else EquipmentStatus.MAINTENANCE
        await db.flush()
        return await MaintenanceService._downtime_detail(db, row)

    @staticmethod
    async def close_downtime(db: AsyncSession, downtime_id: int, obj: CloseDowntime) -> DowntimeDetail:
        row = await MaintenanceService._downtime(db, downtime_id, lock=True)
        if row.status != DowntimeStatus.OPEN:
            raise errors.ConflictError(msg='DOWNTIME_NOT_OPEN')
        await MaintenanceService._close_downtime_row(db, row, obj.end_at or timezone.now(), obj.remark)
        equipment = await MaintenanceService._equipment(
            db, row.equipment_id, require_maintenance_enabled=False
        )
        await MaintenanceService._restore_equipment_status(db, equipment)
        await db.flush()
        return await MaintenanceService._downtime_detail(db, row)

    @staticmethod
    async def dashboard(db: AsyncSession) -> MaintenanceDashboard:
        now = timezone.now()
        today = now.date()
        since = now - timedelta(days=30)
        active_plans = await db.scalar(select(func.count(MaintenancePlan.id)).where(MaintenancePlan.status == PlanStatus.ACTIVE, MaintenancePlan.deleted == 0)) or 0
        pending_tasks = await db.scalar(select(func.count(MaintenanceTask.id)).where(MaintenanceTask.status == TaskStatus.PENDING, MaintenanceTask.deleted == 0)) or 0
        overdue_tasks = await db.scalar(select(func.count(MaintenanceTask.id)).where(MaintenanceTask.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)), MaintenanceTask.due_date < today, MaintenanceTask.deleted == 0)) or 0
        in_progress_tasks = await db.scalar(select(func.count(MaintenanceTask.id)).where(MaintenanceTask.status == TaskStatus.IN_PROGRESS, MaintenanceTask.deleted == 0)) or 0
        open_repairs = await db.scalar(select(func.count(RepairOrder.id)).where(RepairOrder.status.in_((RepairStatus.REPORTED, RepairStatus.ASSIGNED, RepairStatus.IN_REPAIR)), RepairOrder.deleted == 0)) or 0
        critical_repairs = await db.scalar(select(func.count(RepairOrder.id)).where(RepairOrder.fault_level == FaultLevel.CRITICAL, RepairOrder.status.in_((RepairStatus.REPORTED, RepairStatus.ASSIGNED, RepairStatus.IN_REPAIR)), RepairOrder.deleted == 0)) or 0
        open_downtimes = await db.scalar(select(func.count(EquipmentDowntime.id)).where(EquipmentDowntime.status == DowntimeStatus.OPEN, EquipmentDowntime.deleted == 0)) or 0
        overlap_rows = (await db.scalars(select(EquipmentDowntime).where(
            EquipmentDowntime.start_at <= now,
            (EquipmentDowntime.end_at.is_(None) | (EquipmentDowntime.end_at >= since)),
            EquipmentDowntime.status.in_((DowntimeStatus.OPEN, DowntimeStatus.CLOSED)),
            EquipmentDowntime.deleted == 0,
        ))).all()
        total_minutes = sum(
            (
                duration_minutes(max(row.start_at, since), min(row.end_at or now, now))
                for row in overlap_rows
                if min(row.end_at or now, now) > max(row.start_at, since)
            ),
            Decimal('0'),
        )
        completed_30d = await db.scalar(select(func.count(MaintenanceTask.id)).where(MaintenanceTask.status == TaskStatus.COMPLETED, MaintenanceTask.completed_at >= since, MaintenanceTask.deleted == 0)) or 0
        due_30d = await db.scalar(select(func.count(MaintenanceTask.id)).where(MaintenanceTask.due_date >= since.date(), MaintenanceTask.due_date <= today, MaintenanceTask.deleted == 0)) or 0
        rate = (Decimal(completed_30d) / Decimal(due_30d) * Decimal('100')).quantize(Decimal('0.01')) if due_30d else Decimal('0')
        return MaintenanceDashboard(
            active_plans=int(active_plans),
            pending_tasks=int(pending_tasks),
            overdue_tasks=int(overdue_tasks),
            in_progress_tasks=int(in_progress_tasks),
            open_repairs=int(open_repairs),
            critical_repairs=int(critical_repairs),
            open_downtimes=int(open_downtimes),
            downtime_minutes_30d=total_minutes.quantize(Decimal('0.0001')),
            completion_rate_30d=rate,
        )


maintenance_service = MaintenanceService()
