from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.app.admin.model.user import User
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.maintenance.enums import DowntimeCategory, DowntimeStatus
from backend.plugin.maintenance.model import EquipmentDowntime
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import WorkOrder, WorkOrderOperation
from backend.plugin.routing.enums import RunTimeUnit, WorkCenterStatus
from backend.plugin.routing.model import Routing, RoutingOperation, WorkCenter
from backend.plugin.scheduling.crud import scheduling_repository
from backend.plugin.scheduling.enums import (
    ConfigStatus,
    DispatchStatus,
    OperationScheduleStatus,
    ScheduleStatus,
    SchedulingDirection,
)
from backend.plugin.scheduling.model import (
    ApsDispatch,
    ApsOperationSchedule,
    ApsSchedule,
    CalendarDay,
    Shift,
    WorkCalendar,
    WorkCenterCalendar,
    ProductionTeam,
    Workstation,
)
from backend.plugin.scheduling.schema.scheduling import (
    ApsScheduleDetail,
    ApsScheduleListItem,
    AssignWorkCenterCalendar,
    CalendarDayDetail,
    CalendarDetail,
    CreateApsSchedule,
    CreateCalendar,
    CreateDispatch,
    CreateShift,
    DispatchDetail,
    OperationScheduleDetail,
    ShiftDetail,
    UpdateCalendar,
    UpdateShift,
    UpsertCalendarDay,
    WorkCenterCalendarDetail,
    WorkCenterLoad,
    WorkOrderCandidate,
)
from backend.utils.timezone import timezone


MINUTE = Decimal('0.0001')


def _minutes(value: Decimal) -> Decimal:
    return value.quantize(MINUTE, rounding=ROUND_HALF_UP)


def calculate_operation_minutes(
    *,
    quantity: Decimal,
    base_quantity: Decimal,
    routing_operation: RoutingOperation,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return setup, run, queue and move minutes for one routing operation."""

    setup = Decimal(routing_operation.setup_time_min)
    factor = quantity / base_quantity
    run = Decimal(routing_operation.run_time_value) * factor
    if routing_operation.run_time_unit == RunTimeUnit.HOUR_PER_BASE_QTY:
        run *= Decimal('60')
    elif routing_operation.run_time_unit == RunTimeUnit.SEC_PER_BASE_QTY:
        run /= Decimal('60')
    return (
        _minutes(setup),
        _minutes(run),
        _minutes(Decimal(routing_operation.queue_time_min)),
        _minutes(Decimal(routing_operation.move_time_min)),
    )


@dataclass(slots=True)
class WorkingWindow:
    start: datetime
    end: datetime
    capacity_factor: Decimal


class CalendarResolver:
    """Resolve effective work-center working windows for a scheduling horizon."""

    def __init__(
        self,
        *,
        shifts: dict[int, Shift],
        calendars: dict[int, WorkCalendar],
        days: dict[tuple[int, date], CalendarDay],
        assignments: dict[int, list[WorkCenterCalendar]],
        downtimes: dict[int, list[tuple[datetime, datetime]]] | None = None,
    ) -> None:
        self.shifts = shifts
        self.calendars = calendars
        self.days = days
        self.assignments = assignments
        self.downtimes = downtimes or {}

    @classmethod
    async def build(
        cls,
        db: AsyncSession,
        start_at: datetime,
        end_at: datetime,
        *,
        downtime_categories: set[DowntimeCategory] | None = None,
    ) -> 'CalendarResolver':
        shifts = {
            row.id: row
            for row in (
                await db.scalars(
                    select(Shift).where(Shift.deleted == 0, Shift.status == ConfigStatus.ACTIVE)
                )
            ).all()
        }
        calendars = {
            row.id: row
            for row in (
                await db.scalars(
                    select(WorkCalendar).where(
                        WorkCalendar.deleted == 0, WorkCalendar.status == ConfigStatus.ACTIVE
                    )
                )
            ).all()
        }
        days = {
            (row.calendar_id, row.work_date): row
            for row in (
                await db.scalars(
                    select(CalendarDay).where(
                        CalendarDay.deleted == 0,
                        CalendarDay.work_date >= start_at.date() - timedelta(days=2),
                        CalendarDay.work_date <= end_at.date() + timedelta(days=2),
                    )
                )
            ).all()
        }
        assignments: dict[int, list[WorkCenterCalendar]] = defaultdict(list)
        rows = (
            await db.scalars(
                select(WorkCenterCalendar)
                .where(
                    WorkCenterCalendar.deleted == 0,
                    WorkCenterCalendar.effective_from <= end_at.date(),
                    or_(
                        WorkCenterCalendar.effective_to.is_(None),
                        WorkCenterCalendar.effective_to >= start_at.date(),
                    ),
                )
                .order_by(
                    WorkCenterCalendar.work_center_id,
                    WorkCenterCalendar.priority.desc(),
                    WorkCenterCalendar.effective_from.desc(),
                )
            )
        ).all()
        for row in rows:
            if row.calendar_id in calendars:
                assignments[row.work_center_id].append(row)
        downtimes: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
        downtime_rows: list[EquipmentDowntime] = []
        if downtime_categories is None or downtime_categories:
            downtime_stmt = select(EquipmentDowntime).where(
                EquipmentDowntime.deleted == 0,
                EquipmentDowntime.affects_capacity.is_(True),
                EquipmentDowntime.work_center_id.is_not(None),
                EquipmentDowntime.status.in_((DowntimeStatus.OPEN, DowntimeStatus.CLOSED)),
                EquipmentDowntime.start_at < end_at,
                or_(EquipmentDowntime.end_at.is_(None), EquipmentDowntime.end_at > start_at),
            )
            if downtime_categories is not None:
                downtime_stmt = downtime_stmt.where(
                    EquipmentDowntime.category.in_(
                        [category.value for category in downtime_categories]
                    )
                )
            downtime_rows = list((await db.scalars(downtime_stmt)).all())
        for downtime in downtime_rows:
            downtimes[downtime.work_center_id].append(
                (max(downtime.start_at, start_at), min(downtime.end_at or end_at, end_at))
            )
        return cls(
            shifts=shifts,
            calendars=calendars,
            days=days,
            assignments=assignments,
            downtimes=downtimes,
        )

    def _assignment(self, work_center_id: int, day: date) -> WorkCenterCalendar | None:
        for item in self.assignments.get(work_center_id, []):
            if item.effective_from <= day and (item.effective_to is None or item.effective_to >= day):
                return item
        return None

    def window(self, work_center_id: int, day: date) -> WorkingWindow | None:
        assignment = self._assignment(work_center_id, day)
        if assignment is None:
            if day.isoweekday() > 5:
                return None
            start_at = datetime.combine(day, time(8, 0), tzinfo=timezone.tz_info)
            end_at = datetime.combine(day, time(17, 0), tzinfo=timezone.tz_info)
            return WorkingWindow(start=start_at, end=end_at, capacity_factor=Decimal('1'))

        calendar = self.calendars[assignment.calendar_id]
        override = self.days.get((calendar.id, day))
        if override is not None and not override.is_working_day:
            return None
        if override is None and day.isoweekday() not in {
            int(item) for item in calendar.weekday_mask.split(',') if item
        }:
            return None
        shift_id = override.shift_id if override and override.shift_id else calendar.default_shift_id
        shift = self.shifts.get(shift_id) if shift_id else None
        if shift is None:
            return None
        start_at = datetime.combine(day, shift.start_time, tzinfo=timezone.tz_info)
        end_day = day + timedelta(days=1) if shift.spans_next_day else day
        end_at = datetime.combine(end_day, shift.end_time, tzinfo=timezone.tz_info)
        end_at -= timedelta(minutes=shift.break_minutes)
        factor = Decimal(assignment.capacity_factor)
        if override is not None:
            factor *= Decimal(override.capacity_factor)
        if factor <= 0 or end_at <= start_at:
            return None
        return WorkingWindow(start=start_at, end=end_at, capacity_factor=factor)

    def available_segments(self, work_center_id: int, window: WorkingWindow | None) -> list[WorkingWindow]:
        if window is None:
            return []
        segments = [(window.start, window.end)]
        for blocked_start, blocked_end in self.downtimes.get(work_center_id, []):
            remaining: list[tuple[datetime, datetime]] = []
            for start_at, end_at in segments:
                if blocked_end <= start_at or blocked_start >= end_at:
                    remaining.append((start_at, end_at))
                    continue
                if blocked_start > start_at:
                    remaining.append((start_at, min(blocked_start, end_at)))
                if blocked_end < end_at:
                    remaining.append((max(blocked_end, start_at), end_at))
            segments = remaining
        return [
            WorkingWindow(start=start_at, end=end_at, capacity_factor=window.capacity_factor)
            for start_at, end_at in segments
            if end_at > start_at
        ]

    def forward(self, work_center_id: int, earliest: datetime, duration_minutes: Decimal) -> tuple[datetime, datetime]:
        remaining = max(duration_minutes, Decimal('0.0001'))
        cursor = earliest
        first_start: datetime | None = None
        for _ in range(3660):
            base_windows = [
                self.window(work_center_id, cursor.date() - timedelta(days=1)),
                self.window(work_center_id, cursor.date()),
            ]
            windows = [segment for base in base_windows for segment in self.available_segments(work_center_id, base)]
            for window in sorted(windows, key=lambda item: item.start):
                if cursor >= window.end:
                    continue
                current = max(cursor, window.start)
                if current >= window.end:
                    continue
                first_start = first_start or current
                available = Decimal(str((window.end - current).total_seconds() / 60))
                if available >= remaining:
                    return first_start, current + timedelta(minutes=float(remaining))
                remaining -= available
                cursor = window.end
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min, tzinfo=timezone.tz_info)
        raise errors.ConflictError(msg='APS_NO_FORWARD_CAPACITY_WINDOW')

    def backward(self, work_center_id: int, latest: datetime, duration_minutes: Decimal) -> tuple[datetime, datetime]:
        remaining = max(duration_minutes, Decimal('0.0001'))
        cursor = latest
        final_end: datetime | None = None
        for _ in range(3660):
            base_windows = [
                self.window(work_center_id, cursor.date()),
                self.window(work_center_id, cursor.date() - timedelta(days=1)),
            ]
            windows = [segment for base in base_windows for segment in self.available_segments(work_center_id, base)]
            for window in sorted(windows, key=lambda item: item.end, reverse=True):
                if cursor <= window.start:
                    continue
                current = min(cursor, window.end)
                if current <= window.start:
                    continue
                final_end = final_end or current
                available = Decimal(str((current - window.start).total_seconds() / 60))
                if available >= remaining:
                    return current - timedelta(minutes=float(remaining)), final_end
                remaining -= available
                cursor = window.start
            previous = cursor.date() - timedelta(days=1)
            cursor = datetime.combine(previous, time.max, tzinfo=timezone.tz_info)
        raise errors.ConflictError(msg='APS_NO_BACKWARD_CAPACITY_WINDOW')

    def available_minutes(self, center: WorkCenter, start_at: datetime, end_at: datetime) -> Decimal:
        total = Decimal('0')
        # Start one day earlier so a cross-midnight shift can contribute its
        # after-midnight portion to the requested horizon.
        day = start_at.date() - timedelta(days=1)
        while day <= end_at.date():
            for window in self.available_segments(center.id, self.window(center.id, day)):
                overlap_start = max(start_at, window.start)
                overlap_end = min(end_at, window.end)
                if overlap_end > overlap_start:
                    minutes = Decimal(str((overlap_end - overlap_start).total_seconds() / 60))
                    total += minutes * window.capacity_factor * Decimal(max(center.parallel_capacity, 1))
            day += timedelta(days=1)
        return _minutes(total)


class SchedulingService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _shift(db: AsyncSession, shift_id: int) -> Shift:
        row = await db.scalar(select(Shift).where(Shift.id == shift_id, Shift.deleted == 0))
        if not row:
            raise errors.NotFoundError(msg='APS_SHIFT_NOT_FOUND')
        return row

    @staticmethod
    async def _calendar(db: AsyncSession, calendar_id: int) -> WorkCalendar:
        row = await db.scalar(
            select(WorkCalendar).where(WorkCalendar.id == calendar_id, WorkCalendar.deleted == 0)
        )
        if not row:
            raise errors.NotFoundError(msg='APS_CALENDAR_NOT_FOUND')
        return row

    @staticmethod
    async def list_shifts(db: AsyncSession) -> list[ShiftDetail]:
        return [ShiftDetail.model_validate(row) for row in await scheduling_repository.shifts(db)]

    @staticmethod
    async def create_shift(db: AsyncSession, obj: CreateShift) -> ShiftDetail:
        if await db.scalar(
            select(Shift.id).where(Shift.shift_code == obj.shift_code, Shift.deleted == 0)
        ):
            raise errors.ConflictError(msg='APS_SHIFT_CODE_EXISTS')
        row = Shift(**obj.model_dump())
        row.created_by = SchedulingService._operator_id()
        db.add(row)
        await db.flush()
        return ShiftDetail.model_validate(row)

    @staticmethod
    async def update_shift(db: AsyncSession, shift_id: int, obj: UpdateShift) -> ShiftDetail:
        row = await SchedulingService._shift(db, shift_id)
        duplicate = await db.scalar(
            select(Shift.id).where(
                Shift.shift_code == obj.shift_code, Shift.id != shift_id, Shift.deleted == 0
            )
        )
        if duplicate:
            raise errors.ConflictError(msg='APS_SHIFT_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(row, key, value)
        row.updated_by = SchedulingService._operator_id()
        await db.flush()
        return ShiftDetail.model_validate(row)

    @staticmethod
    async def _validate_shift(db: AsyncSession, shift_id: int | None) -> None:
        if shift_id is None:
            return
        shift = await SchedulingService._shift(db, shift_id)
        if shift.status != ConfigStatus.ACTIVE:
            raise errors.ConflictError(msg='APS_SHIFT_DISABLED')

    @staticmethod
    async def list_calendars(db: AsyncSession) -> list[CalendarDetail]:
        return [await SchedulingService.calendar_detail(db, row) for row in await scheduling_repository.calendars(db)]

    @staticmethod
    async def calendar_detail(db: AsyncSession, calendar: WorkCalendar | int) -> CalendarDetail:
        row = await SchedulingService._calendar(db, calendar) if isinstance(calendar, int) else calendar
        result = CalendarDetail.model_validate(row)
        if row.default_shift_id:
            shift = await db.scalar(
                select(Shift).where(Shift.id == row.default_shift_id, Shift.deleted == 0)
            )
            result.default_shift_name = shift.shift_name if shift else None
        result.days = [
            CalendarDayDetail.model_validate(item)
            for item in (
                await db.scalars(
                    select(CalendarDay)
                    .where(CalendarDay.calendar_id == row.id, CalendarDay.deleted == 0)
                    .order_by(CalendarDay.work_date.desc())
                    .limit(366)
                )
            ).all()
        ]
        assignment_rows = (
            await db.execute(
                select(WorkCenterCalendar, WorkCenter)
                .join(WorkCenter, WorkCenter.id == WorkCenterCalendar.work_center_id)
                .where(
                    WorkCenterCalendar.calendar_id == row.id,
                    WorkCenterCalendar.deleted == 0,
                    WorkCenter.deleted == 0,
                )
                .order_by(WorkCenterCalendar.priority.desc(), WorkCenter.work_center_code)
            )
        ).all()
        result.assignments = []
        for assignment, center in assignment_rows:
            item = WorkCenterCalendarDetail.model_validate(assignment)
            item.work_center_code = center.work_center_code
            item.work_center_name = center.work_center_name
            result.assignments.append(item)
        return result

    @staticmethod
    async def create_calendar(db: AsyncSession, obj: CreateCalendar) -> CalendarDetail:
        await SchedulingService._validate_shift(db, obj.default_shift_id)
        if await db.scalar(
            select(WorkCalendar.id).where(
                WorkCalendar.calendar_code == obj.calendar_code, WorkCalendar.deleted == 0
            )
        ):
            raise errors.ConflictError(msg='APS_CALENDAR_CODE_EXISTS')
        row = WorkCalendar(**obj.model_dump())
        row.created_by = SchedulingService._operator_id()
        db.add(row)
        await db.flush()
        return await SchedulingService.calendar_detail(db, row)

    @staticmethod
    async def update_calendar(
        db: AsyncSession, calendar_id: int, obj: UpdateCalendar
    ) -> CalendarDetail:
        row = await SchedulingService._calendar(db, calendar_id)
        await SchedulingService._validate_shift(db, obj.default_shift_id)
        duplicate = await db.scalar(
            select(WorkCalendar.id).where(
                WorkCalendar.calendar_code == obj.calendar_code,
                WorkCalendar.id != calendar_id,
                WorkCalendar.deleted == 0,
            )
        )
        if duplicate:
            raise errors.ConflictError(msg='APS_CALENDAR_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(row, key, value)
        row.updated_by = SchedulingService._operator_id()
        await db.flush()
        return await SchedulingService.calendar_detail(db, row)

    @staticmethod
    async def upsert_calendar_day(
        db: AsyncSession, calendar_id: int, obj: UpsertCalendarDay
    ) -> CalendarDetail:
        calendar = await SchedulingService._calendar(db, calendar_id)
        await SchedulingService._validate_shift(db, obj.shift_id)
        row = await db.scalar(
            select(CalendarDay).where(
                CalendarDay.calendar_id == calendar_id,
                CalendarDay.work_date == obj.work_date,
                CalendarDay.deleted == 0,
            )
        )
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = CalendarDay(calendar_id=calendar_id, **obj.model_dump())
            db.add(row)
        await db.flush()
        return await SchedulingService.calendar_detail(db, calendar)

    @staticmethod
    async def assign_work_center(
        db: AsyncSession, calendar_id: int, obj: AssignWorkCenterCalendar
    ) -> CalendarDetail:
        calendar = await SchedulingService._calendar(db, calendar_id)
        if calendar.status != ConfigStatus.ACTIVE:
            raise errors.ConflictError(msg='APS_CALENDAR_DISABLED')
        center = await db.scalar(
            select(WorkCenter).where(WorkCenter.id == obj.work_center_id, WorkCenter.deleted == 0)
        )
        if not center:
            raise errors.NotFoundError(msg='WORK_CENTER_NOT_FOUND')
        if not center.scheduling_enabled or center.status != WorkCenterStatus.ACTIVE:
            raise errors.ConflictError(msg='WORK_CENTER_NOT_SCHEDULABLE')
        duplicate = await db.scalar(
            select(WorkCenterCalendar).where(
                WorkCenterCalendar.work_center_id == obj.work_center_id,
                WorkCenterCalendar.effective_from == obj.effective_from,
                WorkCenterCalendar.deleted == 0,
            )
        )
        if duplicate:
            duplicate.calendar_id = calendar_id
            duplicate.effective_to = obj.effective_to
            duplicate.capacity_factor = obj.capacity_factor
            duplicate.priority = obj.priority
        else:
            db.add(WorkCenterCalendar(calendar_id=calendar_id, **obj.model_dump()))
        await db.flush()
        return await SchedulingService.calendar_detail(db, calendar)

    @staticmethod
    async def work_order_candidates(db: AsyncSession) -> list[WorkOrderCandidate]:
        rows = (
            await db.execute(
                select(WorkOrder, func.count(WorkOrderOperation.id))
                .outerjoin(
                    WorkOrderOperation,
                    and_(
                        WorkOrderOperation.work_order_id == WorkOrder.id,
                        WorkOrderOperation.deleted == 0,
                    ),
                )
                .where(
                    WorkOrder.deleted == 0,
                    WorkOrder.status.in_((WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED)),
                )
                .group_by(WorkOrder.id)
                .order_by(WorkOrder.planned_end_at, WorkOrder.id)
            )
        ).all()
        return [
            WorkOrderCandidate(
                id=order.id,
                work_order_no=order.work_order_no,
                product_code=order.product_code_snapshot,
                product_name=order.product_name_snapshot,
                planned_quantity=order.planned_quantity,
                status=order.status.value if hasattr(order.status, 'value') else str(order.status),
                operation_count=int(operation_count),
                planned_start_at=order.planned_start_at,
                planned_end_at=order.planned_end_at,
            )
            for order, operation_count in rows
        ]

    @staticmethod
    async def _schedule(db: AsyncSession, schedule_id: int, *, lock: bool = False) -> ApsSchedule:
        stmt = select(ApsSchedule).where(ApsSchedule.id == schedule_id, ApsSchedule.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='APS_SCHEDULE_NOT_FOUND')
        return row

    @staticmethod
    async def list_schedules(db: AsyncSession) -> list[ApsScheduleListItem]:
        return [ApsScheduleListItem.model_validate(row) for row in await scheduling_repository.schedules(db)]

    @staticmethod
    async def schedule_detail(db: AsyncSession, schedule: ApsSchedule | int) -> ApsScheduleDetail:
        row = await SchedulingService._schedule(db, schedule) if isinstance(schedule, int) else schedule
        result = ApsScheduleDetail.model_validate(row)
        result.operations = [
            OperationScheduleDetail.model_validate(item)
            for item in (
                await db.scalars(
                    select(ApsOperationSchedule)
                    .where(ApsOperationSchedule.schedule_id == row.id, ApsOperationSchedule.deleted == 0)
                    .order_by(
                        ApsOperationSchedule.work_center_code_snapshot,
                        ApsOperationSchedule.planned_start_at,
                        ApsOperationSchedule.lane_no,
                    )
                )
            ).all()
        ]
        return result

    @staticmethod
    async def run_schedule(db: AsyncSession, obj: CreateApsSchedule) -> ApsScheduleDetail:
        schedule_no = obj.schedule_no or f'APS-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'
        if await db.scalar(
            select(ApsSchedule.id).where(
                ApsSchedule.schedule_no == schedule_no, ApsSchedule.deleted == 0
            )
        ):
            raise errors.ConflictError(msg='APS_SCHEDULE_NO_EXISTS')
        operator_id = SchedulingService._operator_id()
        now = timezone.now()
        header = ApsSchedule(
            schedule_no=schedule_no,
            schedule_name=obj.schedule_name,
            direction=obj.direction,
            horizon_start_at=obj.horizon_start_at,
            horizon_end_at=obj.horizon_end_at,
            include_queue_time=obj.include_queue_time,
            include_move_time=obj.include_move_time,
            started_at=now,
            remark=obj.remark,
        )
        header.created_by = operator_id
        db.add(header)
        await db.flush()

        order_rows = list(
            (
                await db.scalars(
                    select(WorkOrder).where(
                        WorkOrder.id.in_(obj.work_order_ids),
                        WorkOrder.deleted == 0,
                        WorkOrder.status.in_((WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED)),
                    )
                )
            ).all()
        )
        if len(order_rows) != len(obj.work_order_ids):
            raise errors.ConflictError(msg='APS_WORK_ORDER_NOT_SCHEDULABLE')
        resolver = await CalendarResolver.build(db, obj.horizon_start_at, obj.horizon_end_at)
        forward_lanes: dict[tuple[int, int], datetime] = {}
        backward_lanes: dict[tuple[int, int], datetime] = {}
        order_rows.sort(
            key=lambda item: (item.planned_end_at or obj.horizon_end_at, item.id),
            reverse=obj.direction == SchedulingDirection.BACKWARD,
        )
        overdue_count = 0
        operation_count = 0

        for order in order_rows:
            routing = await db.scalar(
                select(Routing).where(Routing.id == order.routing_id, Routing.deleted == 0)
            )
            if not routing or routing.base_quantity <= 0:
                raise errors.ConflictError(msg=f'APS_ROUTING_INVALID:{order.work_order_no}')
            operations = list(
                (
                    await db.scalars(
                        select(WorkOrderOperation)
                        .where(
                            WorkOrderOperation.work_order_id == order.id,
                            WorkOrderOperation.deleted == 0,
                        )
                        .order_by(WorkOrderOperation.sequence_no)
                    )
                ).all()
            )
            if not operations:
                raise errors.ConflictError(msg=f'APS_WORK_ORDER_HAS_NO_OPERATIONS:{order.work_order_no}')
            if obj.direction == SchedulingDirection.BACKWARD:
                operations.reverse()
                precedence_cursor = min(order.planned_end_at or obj.horizon_end_at, obj.horizon_end_at)
            else:
                precedence_cursor = max(order.planned_start_at or obj.horizon_start_at, obj.horizon_start_at)

            for operation in operations:
                if not operation.work_center_id:
                    raise errors.ConflictError(msg=f'APS_OPERATION_WORK_CENTER_REQUIRED:{order.work_order_no}:{operation.sequence_no}')
                center = await db.scalar(
                    select(WorkCenter).where(
                        WorkCenter.id == operation.work_center_id, WorkCenter.deleted == 0
                    )
                )
                if (
                    not center
                    or center.status != WorkCenterStatus.ACTIVE
                    or not center.production_enabled
                    or not center.scheduling_enabled
                ):
                    raise errors.ConflictError(msg=f'APS_WORK_CENTER_NOT_SCHEDULABLE:{operation.work_center_id}')
                routing_operation = await db.scalar(
                    select(RoutingOperation).where(
                        RoutingOperation.routing_id == order.routing_id,
                        RoutingOperation.sequence_no == operation.sequence_no,
                        RoutingOperation.deleted == 0,
                    )
                )
                if not routing_operation:
                    raise errors.ConflictError(msg=f'APS_ROUTING_OPERATION_MISSING:{order.work_order_no}:{operation.sequence_no}')
                setup, run, queue, move = calculate_operation_minutes(
                    quantity=Decimal(order.planned_quantity),
                    base_quantity=Decimal(routing.base_quantity),
                    routing_operation=routing_operation,
                )
                queue_gap = queue if obj.include_queue_time else Decimal('0')
                move_gap = move if obj.include_move_time else Decimal('0')
                load = _minutes(setup + run)
                lane_count = max(center.parallel_capacity, 1)

                candidates: list[tuple[datetime, datetime, int]] = []
                for lane_no in range(1, lane_count + 1):
                    key = (center.id, lane_no)
                    if obj.direction == SchedulingDirection.FORWARD:
                        earliest = precedence_cursor + timedelta(minutes=float(queue_gap))
                        earliest = max(earliest, forward_lanes.get(key, obj.horizon_start_at))
                        start_at, end_at = resolver.forward(center.id, earliest, load)
                    else:
                        latest = precedence_cursor - timedelta(minutes=float(move_gap))
                        latest = min(latest, backward_lanes.get(key, obj.horizon_end_at))
                        start_at, end_at = resolver.backward(center.id, latest, load)
                    candidates.append((start_at, end_at, lane_no))
                if obj.direction == SchedulingDirection.FORWARD:
                    start_at, end_at, lane_no = min(candidates, key=lambda item: (item[1], item[0], item[2]))
                    forward_lanes[(center.id, lane_no)] = end_at
                    precedence_cursor = end_at + timedelta(minutes=float(move_gap))
                    overdue = end_at > obj.horizon_end_at
                else:
                    start_at, end_at, lane_no = max(candidates, key=lambda item: (item[0], item[1], -item[2]))
                    backward_lanes[(center.id, lane_no)] = start_at
                    precedence_cursor = start_at - timedelta(minutes=float(queue_gap))
                    overdue = start_at < obj.horizon_start_at
                overdue_count += int(overdue)
                operation_count += 1
                db.add(
                    ApsOperationSchedule(
                        schedule_id=header.id,
                        work_order_id=order.id,
                        work_order_operation_id=operation.id,
                        operation_id=operation.operation_id,
                        work_center_id=center.id,
                        sequence_no=operation.sequence_no,
                        lane_no=lane_no,
                        planned_start_at=start_at,
                        planned_end_at=end_at,
                        planned_quantity=order.planned_quantity,
                        setup_minutes=setup,
                        run_minutes=run,
                        queue_minutes=queue_gap,
                        move_minutes=move_gap,
                        load_minutes=load,
                        total_minutes=_minutes(load + queue_gap + move_gap),
                        work_order_no_snapshot=order.work_order_no,
                        product_code_snapshot=order.product_code_snapshot,
                        product_name_snapshot=order.product_name_snapshot,
                        operation_code_snapshot=operation.operation_code_snapshot,
                        operation_name_snapshot=operation.operation_name_snapshot,
                        work_center_code_snapshot=center.work_center_code,
                        work_center_name_snapshot=center.work_center_name,
                        routing_operation_id=routing_operation.id,
                        is_overdue=overdue,
                    )
                )

        header.status = ScheduleStatus.COMPLETED
        header.work_order_count = len(order_rows)
        header.operation_count = operation_count
        header.overdue_operation_count = overdue_count
        header.completed_at = timezone.now()
        await db.flush()
        return await SchedulingService.schedule_detail(db, header)

    @staticmethod
    async def publish_schedule(db: AsyncSession, schedule_id: int) -> ApsScheduleDetail:
        header = await SchedulingService._schedule(db, schedule_id, lock=True)
        if header.status != ScheduleStatus.COMPLETED:
            raise errors.ConflictError(msg='APS_SCHEDULE_NOT_PUBLISHABLE')
        lines = list(
            (
                await db.scalars(
                    select(ApsOperationSchedule).where(
                        ApsOperationSchedule.schedule_id == schedule_id,
                        ApsOperationSchedule.deleted == 0,
                    )
                )
            ).all()
        )
        by_order: dict[int, list[ApsOperationSchedule]] = defaultdict(list)
        for line in lines:
            by_order[line.work_order_id].append(line)
        for order_id, order_lines in by_order.items():
            order = await db.scalar(
                select(WorkOrder)
                .where(WorkOrder.id == order_id, WorkOrder.deleted == 0)
                .with_for_update()
            )
            if not order or order.status not in (WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED):
                raise errors.ConflictError(msg='APS_WORK_ORDER_STATUS_CHANGED')
            order.planned_start_at = min(item.planned_start_at for item in order_lines)
            order.planned_end_at = max(item.planned_end_at for item in order_lines)
            for line in order_lines:
                line.status = OperationScheduleStatus.PUBLISHED
        header.status = ScheduleStatus.PUBLISHED
        header.published_at = timezone.now()
        header.published_by = SchedulingService._operator_id()
        await db.flush()
        return await SchedulingService.schedule_detail(db, header)

    @staticmethod
    async def work_center_loads(db: AsyncSession, schedule_id: int) -> list[WorkCenterLoad]:
        header = await SchedulingService._schedule(db, schedule_id)
        rows = (
            await db.execute(
                select(
                    ApsOperationSchedule.work_center_id,
                    ApsOperationSchedule.work_center_code_snapshot,
                    ApsOperationSchedule.work_center_name_snapshot,
                    func.sum(ApsOperationSchedule.load_minutes),
                    func.count(ApsOperationSchedule.id),
                )
                .where(
                    ApsOperationSchedule.schedule_id == schedule_id,
                    ApsOperationSchedule.deleted == 0,
                    ApsOperationSchedule.status != OperationScheduleStatus.CANCELLED,
                )
                .group_by(
                    ApsOperationSchedule.work_center_id,
                    ApsOperationSchedule.work_center_code_snapshot,
                    ApsOperationSchedule.work_center_name_snapshot,
                )
                .order_by(ApsOperationSchedule.work_center_code_snapshot)
            )
        ).all()
        resolver = await CalendarResolver.build(db, header.horizon_start_at, header.horizon_end_at)
        result: list[WorkCenterLoad] = []
        for center_id, code, name, load, operation_count in rows:
            center = await db.scalar(
                select(WorkCenter).where(WorkCenter.id == center_id, WorkCenter.deleted == 0)
            )
            if not center:
                continue
            available = resolver.available_minutes(center, header.horizon_start_at, header.horizon_end_at)
            scheduled = _minutes(Decimal(load or 0))
            rate = _minutes(scheduled / available * Decimal('100')) if available > 0 else Decimal('0')
            result.append(
                WorkCenterLoad(
                    work_center_id=center.id,
                    work_center_code=code,
                    work_center_name=name,
                    parallel_capacity=max(center.parallel_capacity, 1),
                    available_minutes=available,
                    scheduled_load_minutes=scheduled,
                    utilization_rate=rate,
                    overload_minutes=max(scheduled - available, Decimal('0')),
                    operation_count=int(operation_count),
                )
            )
        return result

    @staticmethod
    async def _dispatch_detail(db: AsyncSession, dispatch: ApsDispatch) -> DispatchDetail:
        line = await db.scalar(
            select(ApsOperationSchedule).where(
                ApsOperationSchedule.id == dispatch.schedule_operation_id,
                ApsOperationSchedule.deleted == 0,
            )
        )
        user = None
        if dispatch.assigned_user_id:
            user = await db.scalar(
                select(User).where(User.id == dispatch.assigned_user_id, User.deleted == 0)
            )
        result = DispatchDetail.model_validate(dispatch)
        if line:
            result.work_order_no = line.work_order_no_snapshot
            result.operation_name = line.operation_name_snapshot
            result.work_center_name = line.work_center_name_snapshot
        result.assigned_username = user.username if user else None
        return result

    @staticmethod
    async def list_dispatches(db: AsyncSession) -> list[DispatchDetail]:
        return [
            await SchedulingService._dispatch_detail(db, row)
            for row in await scheduling_repository.dispatches(db)
        ]

    @staticmethod
    async def create_dispatch(db: AsyncSession, obj: CreateDispatch) -> DispatchDetail:
        line = await db.scalar(
            select(ApsOperationSchedule)
            .where(
                ApsOperationSchedule.id == obj.schedule_operation_id,
                ApsOperationSchedule.deleted == 0,
            )
            .with_for_update()
        )
        if not line or line.status not in (
            OperationScheduleStatus.PUBLISHED,
            OperationScheduleStatus.DISPATCHED,
        ):
            raise errors.ConflictError(msg='APS_OPERATION_NOT_DISPATCHABLE')
        if obj.assigned_user_id:
            user = await db.scalar(
                select(User).where(
                    User.id == obj.assigned_user_id, User.deleted == 0, User.status == 1
                )
            )
            if not user:
                raise errors.NotFoundError(msg='ASSIGNED_USER_NOT_FOUND')
        team = None
        if obj.team_id:
            team = await db.scalar(
                select(ProductionTeam).where(
                    ProductionTeam.id == obj.team_id,
                    ProductionTeam.deleted == 0,
                    ProductionTeam.status == 'ACTIVE',
                )
            )
            if not team:
                raise errors.NotFoundError(msg='PRODUCTION_TEAM_NOT_FOUND')
            if team.work_center_id and team.work_center_id != line.work_center_id:
                raise errors.ConflictError(msg='PRODUCTION_TEAM_CENTER_MISMATCH')
        workstation = None
        if obj.workstation_id:
            workstation = await db.scalar(
                select(Workstation).where(
                    Workstation.id == obj.workstation_id,
                    Workstation.deleted == 0,
                    Workstation.status == 'ACTIVE',
                )
            )
            if not workstation:
                raise errors.NotFoundError(msg='WORKSTATION_NOT_FOUND')
            if workstation.work_center_id != line.work_center_id:
                raise errors.ConflictError(msg='WORKSTATION_CENTER_MISMATCH')
        quantity = obj.dispatch_quantity or line.planned_quantity
        dispatched_quantity = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(ApsDispatch.dispatch_quantity), 0)).where(
                    ApsDispatch.schedule_operation_id == line.id,
                    ApsDispatch.status != DispatchStatus.CANCELLED,
                    ApsDispatch.deleted == 0,
                )
            )
            or 0
        )
        if dispatched_quantity + quantity > line.planned_quantity:
            raise errors.ConflictError(msg='APS_DISPATCH_QUANTITY_EXCEEDS_PLAN')
        now = timezone.now()
        row = ApsDispatch(
            dispatch_no=obj.dispatch_no or f'DSP-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6]}',
            schedule_operation_id=line.id,
            work_order_id=line.work_order_id,
            work_order_operation_id=line.work_order_operation_id,
            work_center_id=line.work_center_id,
            planned_start_at=line.planned_start_at,
            planned_end_at=line.planned_end_at,
            dispatch_quantity=quantity,
            priority=obj.priority,
            assigned_user_id=obj.assigned_user_id,
            team_id=team.id if team else None,
            workstation_id=workstation.id if workstation else None,
            assigned_team=team.team_name if team else obj.assigned_team,
            workstation_code=workstation.workstation_code if workstation else obj.workstation_code,
            dispatched_at=now,
            dispatched_by=SchedulingService._operator_id(),
            remark=obj.remark,
        )
        row.created_by = SchedulingService._operator_id()
        db.add(row)
        line.status = OperationScheduleStatus.DISPATCHED
        line.dispatch_count += 1
        await db.flush()
        return await SchedulingService._dispatch_detail(db, row)

    @staticmethod
    async def _dispatch(db: AsyncSession, dispatch_id: int, *, lock: bool = False) -> ApsDispatch:
        stmt = select(ApsDispatch).where(ApsDispatch.id == dispatch_id, ApsDispatch.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='APS_DISPATCH_NOT_FOUND')
        return row

    @staticmethod
    async def accept_dispatch(db: AsyncSession, dispatch_id: int) -> DispatchDetail:
        row = await SchedulingService._dispatch(db, dispatch_id, lock=True)
        if row.status != DispatchStatus.DISPATCHED:
            raise errors.ConflictError(msg='APS_DISPATCH_NOT_ACCEPTABLE')
        row.status = DispatchStatus.ACCEPTED
        row.accepted_at = timezone.now()
        row.accepted_by = SchedulingService._operator_id()
        await db.flush()
        return await SchedulingService._dispatch_detail(db, row)

    @staticmethod
    async def cancel_dispatch(db: AsyncSession, dispatch_id: int) -> DispatchDetail:
        row = await SchedulingService._dispatch(db, dispatch_id, lock=True)
        if row.status not in (DispatchStatus.DISPATCHED, DispatchStatus.ACCEPTED):
            raise errors.ConflictError(msg='APS_DISPATCH_NOT_CANCELLABLE')
        row.status = DispatchStatus.CANCELLED
        line = await db.scalar(
            select(ApsOperationSchedule)
            .where(ApsOperationSchedule.id == row.schedule_operation_id, ApsOperationSchedule.deleted == 0)
            .with_for_update()
        )
        if line:
            line.dispatch_count = max(line.dispatch_count - 1, 0)
            if line.dispatch_count == 0:
                line.status = OperationScheduleStatus.PUBLISHED
        await db.flush()
        return await SchedulingService._dispatch_detail(db, row)


scheduling_service = SchedulingService()
