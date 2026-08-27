from __future__ import annotations

import calendar

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.equipment.model import Equipment
from backend.plugin.maintenance.enums import DowntimeCategory, DowntimeStatus
from backend.plugin.maintenance.model import EquipmentDowntime
from backend.plugin.performance.enums import MetricGrain, TargetStatus
from backend.plugin.performance.model import PerformanceSnapshot, PerformanceTarget
from backend.plugin.performance.schema.performance import (
    CycleAnalysis,
    DowntimePareto,
    EquipmentReliability,
    PerformanceDashboard,
    PerformanceSnapshotDetail,
    PerformanceTargetDetail,
    PerformanceTargetInput,
    PerformanceTrendPoint,
    RebuildSnapshots,
    SnapshotRebuildResult,
    WorkCenterPerformance,
)
from backend.plugin.production.enums import ProductionExecutionStatus
from backend.plugin.production.model import ProductionExecution, WorkOrder, WorkOrderOperation
from backend.plugin.routing.enums import RunTimeUnit
from backend.plugin.routing.model import Routing, RoutingOperation, WorkCenter
from backend.plugin.scheduling.service.scheduling_service import CalendarResolver
from backend.utils.timezone import timezone


MINUTE = Decimal('0.0001')
QUANTITY = Decimal('0.000001')
PERCENT = Decimal('0.0001')
DEFAULT_AVAILABILITY_TARGET = Decimal('90')
DEFAULT_PERFORMANCE_TARGET = Decimal('95')
DEFAULT_QUALITY_TARGET = Decimal('99')
DEFAULT_OEE_TARGET = Decimal('85')


def quantize(value: Decimal, unit: Decimal = MINUTE) -> Decimal:
    return Decimal(value).quantize(unit, rounding=ROUND_HALF_UP)


def ratio_percent(numerator: Decimal, denominator: Decimal, *, cap: bool = True) -> Decimal:
    if denominator <= 0:
        return Decimal('0.0000')
    value = numerator / denominator * Decimal('100')
    if cap:
        value = min(max(value, Decimal('0')), Decimal('100'))
    return quantize(value, PERCENT)


def enum_value(value: object) -> str:
    return str(getattr(value, 'value', value))


def standard_run_minutes(
    quantity: Decimal,
    run_time_value: Decimal | None,
    run_time_unit: object | None,
    base_quantity: Decimal | None,
) -> Decimal | None:
    if run_time_value is None or base_quantity is None or base_quantity <= 0 or run_time_value <= 0:
        return None
    minutes = Decimal(run_time_value) * Decimal(quantity) / Decimal(base_quantity)
    unit = enum_value(run_time_unit)
    if unit == RunTimeUnit.HOUR_PER_BASE_QTY.value:
        minutes *= Decimal('60')
    elif unit == RunTimeUnit.SEC_PER_BASE_QTY.value:
        minutes /= Decimal('60')
    return quantize(minutes)


def overlap_minutes(
    start_at: datetime,
    end_at: datetime | None,
    period_start: datetime,
    period_end: datetime,
) -> Decimal:
    overlap_start = max(start_at, period_start)
    overlap_end = min(end_at or period_end, period_end)
    if overlap_end <= overlap_start:
        return Decimal('0')
    return quantize(Decimal(str((overlap_end - overlap_start).total_seconds())) / Decimal('60'))


def merged_interval_minutes(
    intervals: list[tuple[datetime, datetime | None]],
    period_start: datetime,
    period_end: datetime,
) -> Decimal:
    clipped: list[tuple[datetime, datetime]] = []
    for start_at, end_at in intervals:
        start = max(start_at, period_start)
        end = min(end_at or period_end, period_end)
        if end > start:
            clipped.append((start, end))
    if not clipped:
        return Decimal('0')
    clipped.sort(key=lambda item: item[0])
    merged: list[tuple[datetime, datetime]] = [clipped[0]]
    for start, end in clipped[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    seconds = sum((end - start).total_seconds() for start, end in merged)
    return quantize(Decimal(str(seconds)) / Decimal('60'))


def resolve_period(
    start_date: date | None,
    end_date: date | None,
    *,
    default_days: int = 30,
    max_days: int = 366,
) -> tuple[date, date, datetime, datetime]:
    resolved_end = end_date or timezone.now().date()
    resolved_start = start_date or (resolved_end - timedelta(days=default_days - 1))
    if resolved_end < resolved_start:
        raise errors.RequestError(msg='PERFORMANCE_END_BEFORE_START')
    if (resolved_end - resolved_start).days >= max_days:
        raise errors.RequestError(msg=f'PERFORMANCE_RANGE_EXCEEDS_{max_days}_DAYS')
    start_at = datetime.combine(resolved_start, time.min, tzinfo=timezone.tz_info)
    end_at = datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=timezone.tz_info)
    return resolved_start, resolved_end, start_at, end_at


def bucket_ranges(start_date: date, end_date: date, grain: MetricGrain) -> list[tuple[date, date]]:
    result: list[tuple[date, date]] = []
    cursor = start_date
    while cursor <= end_date:
        if grain == MetricGrain.DAY:
            bucket_end = cursor
        elif grain == MetricGrain.WEEK:
            bucket_end = min(cursor + timedelta(days=6), end_date)
        else:
            month_end = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
            bucket_end = min(month_end, end_date)
        result.append((cursor, bucket_end))
        cursor = bucket_end + timedelta(days=1)
    return result


@dataclass(slots=True)
class ExecutionFact:
    execution_id: int
    work_center_id: int
    operation_id: int
    operation_code: str
    operation_name: str
    product_code: str
    product_name: str
    started_at: datetime
    completed_at: datetime
    good_quantity: Decimal
    scrap_quantity: Decimal
    ideal_run_minutes: Decimal | None

    @property
    def total_quantity(self) -> Decimal:
        return self.good_quantity + self.scrap_quantity


@dataclass(slots=True)
class DowntimeFact:
    downtime_id: int
    equipment_id: int
    work_center_id: int | None
    category: str
    start_at: datetime
    end_at: datetime | None
    reason: str


@dataclass(slots=True)
class AnalysisContext:
    centers: list[WorkCenter]
    equipment: list[Equipment]
    targets: dict[int, PerformanceTarget]
    executions: list[ExecutionFact]
    downtimes: list[DowntimeFact]
    raw_calendar: CalendarResolver
    planned_calendar: CalendarResolver
    operating_calendar: CalendarResolver
    start_at: datetime
    end_at: datetime


class PerformanceService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _centers(
        db: AsyncSession,
        work_center_ids: list[int] | None = None,
    ) -> list[WorkCenter]:
        stmt = select(WorkCenter).where(WorkCenter.deleted == 0)
        if work_center_ids:
            stmt = stmt.where(WorkCenter.id.in_(work_center_ids))
        rows = list((await db.scalars(stmt.order_by(WorkCenter.work_center_code))).all())
        if work_center_ids and {row.id for row in rows} != set(work_center_ids):
            raise errors.NotFoundError(msg='PERFORMANCE_WORK_CENTER_NOT_FOUND')
        return rows

    @staticmethod
    async def _build_context(
        db: AsyncSession,
        start_at: datetime,
        end_at: datetime,
        work_center_ids: list[int] | None = None,
    ) -> AnalysisContext:
        centers = await PerformanceService._centers(db, work_center_ids)
        center_ids = [center.id for center in centers]
        equipment = list(
            (
                await db.scalars(
                    select(Equipment)
                    .where(Equipment.deleted == 0, Equipment.maintenance_enabled.is_(True))
                    .order_by(Equipment.equipment_code)
                )
            ).all()
        )
        targets: dict[int, PerformanceTarget] = {}
        if center_ids:
            targets = {
                row.work_center_id: row
                for row in (
                    await db.scalars(
                        select(PerformanceTarget).where(
                            PerformanceTarget.work_center_id.in_(center_ids),
                            PerformanceTarget.deleted == 0,
                            PerformanceTarget.status == TargetStatus.ACTIVE,
                        )
                    )
                ).all()
            }

        raw_calendar = await CalendarResolver.build(
            db, start_at, end_at, downtime_categories=set()
        )
        planned_calendar = await CalendarResolver.build(
            db,
            start_at,
            end_at,
            downtime_categories={DowntimeCategory.PLANNED},
        )
        operating_calendar = await CalendarResolver.build(db, start_at, end_at)

        executions: list[ExecutionFact] = []
        if center_ids:
            execution_rows = (
                await db.execute(
                    select(
                        ProductionExecution.id,
                        WorkOrderOperation.work_center_id,
                        WorkOrderOperation.operation_id,
                        WorkOrderOperation.operation_code_snapshot,
                        WorkOrderOperation.operation_name_snapshot,
                        WorkOrder.product_code_snapshot,
                        WorkOrder.product_name_snapshot,
                        ProductionExecution.started_at,
                        ProductionExecution.completed_at,
                        ProductionExecution.good_quantity,
                        ProductionExecution.scrap_quantity,
                        RoutingOperation.run_time_value,
                        RoutingOperation.run_time_unit,
                        Routing.base_quantity,
                    )
                    .join(
                        WorkOrderOperation,
                        WorkOrderOperation.id == ProductionExecution.work_order_operation_id,
                    )
                    .join(WorkOrder, WorkOrder.id == ProductionExecution.work_order_id)
                    .outerjoin(
                        Routing,
                        and_(Routing.id == WorkOrder.routing_id, Routing.deleted == 0),
                    )
                    .outerjoin(
                        RoutingOperation,
                        and_(
                            RoutingOperation.routing_id == WorkOrder.routing_id,
                            RoutingOperation.sequence_no == WorkOrderOperation.sequence_no,
                            RoutingOperation.deleted == 0,
                        ),
                    )
                    .where(
                        ProductionExecution.deleted == 0,
                        ProductionExecution.status == ProductionExecutionStatus.COMPLETED,
                        ProductionExecution.completed_at.is_not(None),
                        ProductionExecution.completed_at >= start_at,
                        ProductionExecution.completed_at < end_at,
                        WorkOrderOperation.work_center_id.in_(center_ids),
                    )
                )
            ).all()
            for row in execution_rows:
                total = Decimal(row.good_quantity) + Decimal(row.scrap_quantity)
                executions.append(
                    ExecutionFact(
                        execution_id=row.id,
                        work_center_id=row.work_center_id,
                        operation_id=row.operation_id,
                        operation_code=row.operation_code_snapshot,
                        operation_name=row.operation_name_snapshot,
                        product_code=row.product_code_snapshot,
                        product_name=row.product_name_snapshot,
                        started_at=row.started_at,
                        completed_at=row.completed_at,
                        good_quantity=Decimal(row.good_quantity),
                        scrap_quantity=Decimal(row.scrap_quantity),
                        ideal_run_minutes=standard_run_minutes(
                            total,
                            Decimal(row.run_time_value) if row.run_time_value is not None else None,
                            row.run_time_unit,
                            Decimal(row.base_quantity) if row.base_quantity is not None else None,
                        ),
                    )
                )

        downtime_rows = (
            await db.execute(
                select(
                    EquipmentDowntime.id,
                    EquipmentDowntime.equipment_id,
                    EquipmentDowntime.work_center_id,
                    EquipmentDowntime.category,
                    EquipmentDowntime.start_at,
                    EquipmentDowntime.end_at,
                    EquipmentDowntime.reason,
                ).where(
                    EquipmentDowntime.deleted == 0,
                    EquipmentDowntime.status.in_((DowntimeStatus.OPEN, DowntimeStatus.CLOSED)),
                    EquipmentDowntime.start_at < end_at,
                    or_(EquipmentDowntime.end_at.is_(None), EquipmentDowntime.end_at > start_at),
                )
            )
        ).all()
        downtimes = [
            DowntimeFact(
                downtime_id=row.id,
                equipment_id=row.equipment_id,
                work_center_id=row.work_center_id,
                category=enum_value(row.category),
                start_at=row.start_at,
                end_at=row.end_at,
                reason=(row.reason or '未填写原因').strip() or '未填写原因',
            )
            for row in downtime_rows
        ]
        return AnalysisContext(
            centers=centers,
            equipment=equipment,
            targets=targets,
            executions=executions,
            downtimes=downtimes,
            raw_calendar=raw_calendar,
            planned_calendar=planned_calendar,
            operating_calendar=operating_calendar,
            start_at=start_at,
            end_at=end_at,
        )

    @staticmethod
    def _target_values(
        target: PerformanceTarget | None,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal | None]:
        if target is None:
            return (
                DEFAULT_AVAILABILITY_TARGET,
                DEFAULT_PERFORMANCE_TARGET,
                DEFAULT_QUALITY_TARGET,
                DEFAULT_OEE_TARGET,
                None,
            )
        return (
            Decimal(target.availability_target),
            Decimal(target.performance_target),
            Decimal(target.quality_target),
            Decimal(target.oee_target),
            Decimal(target.ideal_cycle_seconds) if target.ideal_cycle_seconds is not None else None,
        )

    @staticmethod
    def _center_metric(
        context: AnalysisContext,
        center: WorkCenter,
        start_at: datetime,
        end_at: datetime,
    ) -> WorkCenterPerformance:
        target_values = PerformanceService._target_values(context.targets.get(center.id))
        availability_target, performance_target, quality_target, oee_target, cycle_fallback = target_values
        calendar_minutes = context.raw_calendar.available_minutes(center, start_at, end_at)
        planned_production = context.planned_calendar.available_minutes(center, start_at, end_at)
        operating_minutes = context.operating_calendar.available_minutes(center, start_at, end_at)
        planned_downtime = max(calendar_minutes - planned_production, Decimal('0'))
        unplanned_downtime = max(planned_production - operating_minutes, Decimal('0'))

        facts = [
            fact
            for fact in context.executions
            if fact.work_center_id == center.id and start_at <= fact.completed_at < end_at
        ]
        good = sum((fact.good_quantity for fact in facts), Decimal('0'))
        scrap = sum((fact.scrap_quantity for fact in facts), Decimal('0'))
        total = good + scrap
        actual_run = sum(
            (
                overlap_minutes(fact.started_at, fact.completed_at, start_at, end_at)
                for fact in facts
            ),
            Decimal('0'),
        )
        ideal_run = Decimal('0')
        for fact in facts:
            if fact.ideal_run_minutes is not None:
                ideal_run += fact.ideal_run_minutes
            elif cycle_fallback is not None:
                ideal_run += fact.total_quantity * cycle_fallback / Decimal('60')
        ideal_run = quantize(ideal_run)

        availability = ratio_percent(operating_minutes, planned_production)
        performance = ratio_percent(ideal_run, operating_minutes)
        quality = ratio_percent(good, total)
        oee = quantize(
            availability * performance * quality / Decimal('10000'), PERCENT
        )
        utilization = ratio_percent(actual_run, operating_minutes, cap=False)
        idle_capacity = max(operating_minutes - actual_run, Decimal('0'))
        actual_cycle = quantize(actual_run * Decimal('60') / total, QUANTITY) if total > 0 else None
        ideal_cycle = quantize(ideal_run * Decimal('60') / total, QUANTITY) if total > 0 and ideal_run > 0 else None
        throughput = (
            quantize(good / (operating_minutes / Decimal('60')), QUANTITY)
            if operating_minutes > 0
            else Decimal('0.000000')
        )

        failures = [
            item
            for item in context.downtimes
            if item.work_center_id == center.id
            and item.category == DowntimeCategory.UNPLANNED.value
            and start_at <= item.start_at < end_at
        ]
        failure_minutes = sum(
            (
                overlap_minutes(item.start_at, item.end_at, start_at, end_at)
                for item in failures
            ),
            Decimal('0'),
        )
        failure_count = len(failures)
        lane_count = max(center.parallel_capacity, 1)
        mtbf = (
            quantize(operating_minutes / Decimal(lane_count) / Decimal(failure_count))
            if failure_count
            else None
        )
        mttr = quantize(failure_minutes / Decimal(failure_count)) if failure_count else None
        return WorkCenterPerformance(
            work_center_id=center.id,
            work_center_code=center.work_center_code,
            work_center_name=center.work_center_name,
            parallel_capacity=lane_count,
            calendar_minutes=quantize(calendar_minutes),
            planned_downtime_minutes=quantize(planned_downtime),
            planned_production_minutes=quantize(planned_production),
            unplanned_downtime_minutes=quantize(unplanned_downtime),
            operating_minutes=quantize(operating_minutes),
            actual_run_minutes=quantize(actual_run),
            idle_capacity_minutes=quantize(idle_capacity),
            good_quantity=quantize(good, QUANTITY),
            scrap_quantity=quantize(scrap, QUANTITY),
            total_quantity=quantize(total, QUANTITY),
            ideal_run_minutes=ideal_run,
            availability_rate=availability,
            performance_rate=performance,
            quality_rate=quality,
            oee_rate=oee,
            utilization_rate=utilization,
            actual_cycle_seconds=actual_cycle,
            ideal_cycle_seconds=ideal_cycle,
            throughput_per_hour=throughput,
            failure_count=failure_count,
            mtbf_minutes=mtbf,
            mttr_minutes=mttr,
            source_execution_count=len(facts),
            availability_target=availability_target,
            performance_target=performance_target,
            quality_target=quality_target,
            oee_target=oee_target,
            oee_on_target=oee >= oee_target,
        )

    @staticmethod
    def _work_center_rows(
        context: AnalysisContext,
        start_at: datetime,
        end_at: datetime,
    ) -> list[WorkCenterPerformance]:
        return [
            PerformanceService._center_metric(context, center, start_at, end_at)
            for center in context.centers
        ]

    @staticmethod
    def _dashboard_from_rows(
        rows: list[WorkCenterPerformance], period_start: date, period_end: date
    ) -> PerformanceDashboard:
        def total(field: str) -> Decimal:
            return sum((Decimal(getattr(row, field)) for row in rows), Decimal('0'))

        calendar_minutes = total('calendar_minutes')
        planned_downtime = total('planned_downtime_minutes')
        planned_production = total('planned_production_minutes')
        unplanned_downtime = total('unplanned_downtime_minutes')
        operating_minutes = total('operating_minutes')
        actual_run = total('actual_run_minutes')
        idle_capacity = total('idle_capacity_minutes')
        good = total('good_quantity')
        scrap = total('scrap_quantity')
        quantity_total = good + scrap
        ideal_run = total('ideal_run_minutes')
        availability = ratio_percent(operating_minutes, planned_production)
        performance = ratio_percent(ideal_run, operating_minutes)
        quality = ratio_percent(good, quantity_total)
        oee = quantize(availability * performance * quality / Decimal('10000'), PERCENT)
        utilization = ratio_percent(actual_run, operating_minutes, cap=False)
        actual_cycle = quantize(actual_run * Decimal('60') / quantity_total, QUANTITY) if quantity_total > 0 else None
        ideal_cycle = quantize(ideal_run * Decimal('60') / quantity_total, QUANTITY) if quantity_total > 0 and ideal_run > 0 else None
        throughput = (
            quantize(good / (operating_minutes / Decimal('60')), QUANTITY)
            if operating_minutes > 0
            else Decimal('0.000000')
        )
        failure_count = sum(row.failure_count for row in rows)
        failure_minutes = sum(
            (
                Decimal(row.mttr_minutes or 0) * Decimal(row.failure_count)
                for row in rows
            ),
            Decimal('0'),
        )
        mtbf = quantize(operating_minutes / Decimal(failure_count)) if failure_count else None
        mttr = quantize(failure_minutes / Decimal(failure_count)) if failure_count else None
        target_oee = (
            quantize(
                sum((Decimal(row.oee_target) for row in rows), Decimal('0'))
                / Decimal(len(rows)),
                PERCENT,
            )
            if rows
            else DEFAULT_OEE_TARGET
        )
        return PerformanceDashboard(
            period_start=period_start,
            period_end=period_end,
            work_center_count=len(rows),
            target_oee_rate=target_oee,
            on_target_center_count=sum(1 for row in rows if row.oee_on_target),
            calendar_minutes=quantize(calendar_minutes),
            planned_downtime_minutes=quantize(planned_downtime),
            planned_production_minutes=quantize(planned_production),
            unplanned_downtime_minutes=quantize(unplanned_downtime),
            operating_minutes=quantize(operating_minutes),
            actual_run_minutes=quantize(actual_run),
            idle_capacity_minutes=quantize(idle_capacity),
            good_quantity=quantize(good, QUANTITY),
            scrap_quantity=quantize(scrap, QUANTITY),
            total_quantity=quantize(quantity_total, QUANTITY),
            ideal_run_minutes=quantize(ideal_run),
            availability_rate=availability,
            performance_rate=performance,
            quality_rate=quality,
            oee_rate=oee,
            utilization_rate=utilization,
            actual_cycle_seconds=actual_cycle,
            ideal_cycle_seconds=ideal_cycle,
            throughput_per_hour=throughput,
            failure_count=failure_count,
            mtbf_minutes=mtbf,
            mttr_minutes=mttr,
            source_execution_count=sum(row.source_execution_count for row in rows),
        )

    @staticmethod
    async def dashboard(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        work_center_id: int | None = None,
    ) -> PerformanceDashboard:
        resolved_start, resolved_end, start_at, end_at = resolve_period(start_date, end_date)
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        rows = PerformanceService._work_center_rows(context, start_at, end_at)
        return PerformanceService._dashboard_from_rows(rows, resolved_start, resolved_end)

    @staticmethod
    async def work_centers(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        work_center_id: int | None = None,
    ) -> list[WorkCenterPerformance]:
        _, _, start_at, end_at = resolve_period(start_date, end_date)
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        return PerformanceService._work_center_rows(context, start_at, end_at)

    @staticmethod
    async def trend(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        grain: MetricGrain,
        work_center_id: int | None = None,
    ) -> list[PerformanceTrendPoint]:
        resolved_start, resolved_end, start_at, end_at = resolve_period(start_date, end_date)
        if grain == MetricGrain.DAY and (resolved_end - resolved_start).days > 92:
            raise errors.RequestError(msg='PERFORMANCE_DAILY_TREND_EXCEEDS_93_DAYS')
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        result: list[PerformanceTrendPoint] = []
        for bucket_start, bucket_end in bucket_ranges(resolved_start, resolved_end, grain):
            bucket_start_at = datetime.combine(bucket_start, time.min, tzinfo=timezone.tz_info)
            bucket_end_at = datetime.combine(
                bucket_end + timedelta(days=1), time.min, tzinfo=timezone.tz_info
            )
            dashboard = PerformanceService._dashboard_from_rows(
                PerformanceService._work_center_rows(context, bucket_start_at, bucket_end_at),
                bucket_start,
                bucket_end,
            )
            result.append(
                PerformanceTrendPoint(
                    period_start=bucket_start,
                    period_end=bucket_end,
                    **dashboard.model_dump(
                        exclude={
                            'period_start',
                            'period_end',
                            'work_center_count',
                            'target_oee_rate',
                            'on_target_center_count',
                        }
                    ),
                )
            )
        return result

    @staticmethod
    async def equipment_reliability(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        equipment_id: int | None = None,
        work_center_id: int | None = None,
    ) -> list[EquipmentReliability]:
        _, _, start_at, end_at = resolve_period(start_date, end_date)
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        observation_minutes = quantize(
            Decimal(str((end_at - start_at).total_seconds())) / Decimal('60')
        )
        result: list[EquipmentReliability] = []
        for equipment in context.equipment:
            if equipment_id and equipment.id != equipment_id:
                continue
            rows = [
                row
                for row in context.downtimes
                if row.equipment_id == equipment.id
                and (work_center_id is None or row.work_center_id == work_center_id)
            ]
            if work_center_id and not rows:
                continue
            planned_intervals = [
                (row.start_at, row.end_at)
                for row in rows
                if row.category == DowntimeCategory.PLANNED.value
            ]
            unplanned_intervals = [
                (row.start_at, row.end_at)
                for row in rows
                if row.category == DowntimeCategory.UNPLANNED.value
            ]
            all_intervals = [(row.start_at, row.end_at) for row in rows]
            planned_minutes = merged_interval_minutes(planned_intervals, start_at, end_at)
            unplanned_minutes = merged_interval_minutes(unplanned_intervals, start_at, end_at)
            total_downtime = merged_interval_minutes(all_intervals, start_at, end_at)
            failures = [
                row
                for row in rows
                if row.category == DowntimeCategory.UNPLANNED.value
                and start_at <= row.start_at < end_at
            ]
            failure_count = len(failures)
            mtbf = (
                quantize((observation_minutes - unplanned_minutes) / Decimal(failure_count))
                if failure_count
                else None
            )
            mttr = quantize(unplanned_minutes / Decimal(failure_count)) if failure_count else None
            result.append(
                EquipmentReliability(
                    equipment_id=equipment.id,
                    equipment_code=equipment.equipment_code,
                    equipment_name=equipment.equipment_name,
                    failure_count=failure_count,
                    planned_downtime_minutes=planned_minutes,
                    unplanned_downtime_minutes=unplanned_minutes,
                    total_downtime_minutes=total_downtime,
                    availability_rate=ratio_percent(
                        max(observation_minutes - total_downtime, Decimal('0')),
                        observation_minutes,
                    ),
                    mtbf_minutes=mtbf,
                    mttr_minutes=mttr,
                    last_failure_at=max((row.start_at for row in failures), default=None),
                )
            )
        return sorted(
            result,
            key=lambda item: (
                -item.failure_count,
                -item.unplanned_downtime_minutes,
                item.equipment_code,
            ),
        )

    @staticmethod
    async def cycle_analysis(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        work_center_id: int | None = None,
    ) -> list[CycleAnalysis]:
        _, _, start_at, end_at = resolve_period(start_date, end_date)
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        centers = {center.id: center for center in context.centers}
        groups: dict[tuple, list[ExecutionFact]] = defaultdict(list)
        for fact in context.executions:
            groups[
                (
                    fact.work_center_id,
                    fact.operation_id,
                    fact.operation_code,
                    fact.operation_name,
                    fact.product_code,
                    fact.product_name,
                )
            ].append(fact)
        result: list[CycleAnalysis] = []
        for key, facts in groups.items():
            center_id, operation_id, operation_code, operation_name, product_code, product_name = key
            center = centers.get(center_id)
            if center is None:
                continue
            target = context.targets.get(center_id)
            fallback = (
                Decimal(target.ideal_cycle_seconds)
                if target and target.ideal_cycle_seconds is not None
                else None
            )
            good = sum((fact.good_quantity for fact in facts), Decimal('0'))
            scrap = sum((fact.scrap_quantity for fact in facts), Decimal('0'))
            total = good + scrap
            actual_run = sum(
                (
                    overlap_minutes(fact.started_at, fact.completed_at, start_at, end_at)
                    for fact in facts
                ),
                Decimal('0'),
            )
            ideal_run = sum(
                (
                    fact.ideal_run_minutes
                    if fact.ideal_run_minutes is not None
                    else (fact.total_quantity * fallback / Decimal('60') if fallback else Decimal('0'))
                    for fact in facts
                ),
                Decimal('0'),
            )
            actual_cycle = quantize(actual_run * Decimal('60') / total, QUANTITY) if total > 0 else None
            ideal_cycle = quantize(ideal_run * Decimal('60') / total, QUANTITY) if total > 0 and ideal_run > 0 else None
            result.append(
                CycleAnalysis(
                    work_center_id=center.id,
                    work_center_code=center.work_center_code,
                    work_center_name=center.work_center_name,
                    operation_id=operation_id,
                    operation_code=operation_code,
                    operation_name=operation_name,
                    product_code=product_code,
                    product_name=product_name,
                    execution_count=len(facts),
                    good_quantity=quantize(good, QUANTITY),
                    scrap_quantity=quantize(scrap, QUANTITY),
                    total_quantity=quantize(total, QUANTITY),
                    actual_run_minutes=quantize(actual_run),
                    ideal_run_minutes=quantize(ideal_run),
                    actual_cycle_seconds=actual_cycle,
                    ideal_cycle_seconds=ideal_cycle,
                    cycle_efficiency_rate=(
                        ratio_percent(ideal_cycle, actual_cycle, cap=False)
                        if ideal_cycle is not None and actual_cycle is not None
                        else Decimal('0.0000')
                    ),
                )
            )
        return sorted(result, key=lambda item: (-item.total_quantity, item.work_center_code))

    @staticmethod
    async def downtime_pareto(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        work_center_id: int | None = None,
        top_n: int = 10,
    ) -> list[DowntimePareto]:
        _, _, start_at, end_at = resolve_period(start_date, end_date)
        context = await PerformanceService._build_context(
            db, start_at, end_at, [work_center_id] if work_center_id else None
        )
        groups: dict[str, tuple[int, Decimal]] = {}
        for row in context.downtimes:
            if row.category != DowntimeCategory.UNPLANNED.value:
                continue
            if work_center_id and row.work_center_id != work_center_id:
                continue
            count, minutes = groups.get(row.reason, (0, Decimal('0')))
            groups[row.reason] = (
                count + 1,
                minutes + overlap_minutes(row.start_at, row.end_at, start_at, end_at),
            )
        ordered = sorted(groups.items(), key=lambda item: (-item[1][1], -item[1][0], item[0]))[:top_n]
        total_minutes = sum((value[1] for value in groups.values()), Decimal('0'))
        cumulative = Decimal('0')
        result: list[DowntimePareto] = []
        for index, (reason, (event_count, minutes)) in enumerate(ordered, start=1):
            percentage = ratio_percent(minutes, total_minutes)
            cumulative += percentage
            result.append(
                DowntimePareto(
                    rank=index,
                    reason=reason,
                    event_count=event_count,
                    downtime_minutes=quantize(minutes),
                    percentage=percentage,
                    cumulative_percentage=min(quantize(cumulative, PERCENT), Decimal('100')),
                )
            )
        return result

    @staticmethod
    async def targets(db: AsyncSession) -> list[PerformanceTargetDetail]:
        centers = await PerformanceService._centers(db)
        rows = {
            row.work_center_id: row
            for row in (
                await db.scalars(
                    select(PerformanceTarget).where(PerformanceTarget.deleted == 0)
                )
            ).all()
        }
        result: list[PerformanceTargetDetail] = []
        for center in centers:
            row = rows.get(center.id)
            if row:
                detail = PerformanceTargetDetail.model_validate(row)
                detail.work_center_code = center.work_center_code
                detail.work_center_name = center.work_center_name
                detail.configured = True
            else:
                detail = PerformanceTargetDetail(
                    work_center_id=center.id,
                    work_center_code=center.work_center_code,
                    work_center_name=center.work_center_name,
                )
            result.append(detail)
        return result

    @staticmethod
    async def upsert_target(
        db: AsyncSession,
        work_center_id: int,
        obj: PerformanceTargetInput,
    ) -> PerformanceTargetDetail:
        centers = await PerformanceService._centers(db, [work_center_id])
        center = centers[0]
        row = await db.scalar(
            select(PerformanceTarget)
            .where(
                PerformanceTarget.work_center_id == work_center_id,
                PerformanceTarget.deleted == 0,
            )
            .with_for_update()
        )
        data = obj.model_dump()
        if row is None:
            row = PerformanceTarget(work_center_id=work_center_id, **data)
            row.created_by = PerformanceService._operator_id()
            db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
            row.updated_by = PerformanceService._operator_id()
        await db.flush()
        detail = PerformanceTargetDetail.model_validate(row)
        detail.work_center_code = center.work_center_code
        detail.work_center_name = center.work_center_name
        detail.configured = True
        return detail

    @staticmethod
    def _snapshot_values(row: WorkCenterPerformance) -> dict:
        return row.model_dump(
            include={
                'calendar_minutes',
                'planned_downtime_minutes',
                'planned_production_minutes',
                'unplanned_downtime_minutes',
                'operating_minutes',
                'actual_run_minutes',
                'idle_capacity_minutes',
                'good_quantity',
                'scrap_quantity',
                'total_quantity',
                'ideal_run_minutes',
                'availability_rate',
                'performance_rate',
                'quality_rate',
                'oee_rate',
                'utilization_rate',
                'actual_cycle_seconds',
                'ideal_cycle_seconds',
                'throughput_per_hour',
                'failure_count',
                'mtbf_minutes',
                'mttr_minutes',
                'source_execution_count',
            }
        )

    @staticmethod
    async def rebuild_snapshots(
        db: AsyncSession,
        obj: RebuildSnapshots,
    ) -> SnapshotRebuildResult:
        _, _, start_at, end_at = resolve_period(
            obj.start_date, obj.end_date, default_days=1, max_days=94
        )
        context = await PerformanceService._build_context(
            db, start_at, end_at, obj.work_center_ids or None
        )
        center_ids = [center.id for center in context.centers]
        existing_rows = []
        if center_ids:
            existing_rows = list(
                (
                    await db.scalars(
                        select(PerformanceSnapshot)
                        .where(
                            PerformanceSnapshot.metric_date >= obj.start_date,
                            PerformanceSnapshot.metric_date <= obj.end_date,
                            PerformanceSnapshot.work_center_id.in_(center_ids),
                            PerformanceSnapshot.deleted == 0,
                        )
                        .with_for_update()
                    )
                ).all()
            )
        existing = {(row.metric_date, row.work_center_id): row for row in existing_rows}
        calculated_at = timezone.now()
        snapshot_count = 0
        current = obj.start_date
        while current <= obj.end_date:
            day_start = datetime.combine(current, time.min, tzinfo=timezone.tz_info)
            day_end = day_start + timedelta(days=1)
            for metric in PerformanceService._work_center_rows(context, day_start, day_end):
                values = PerformanceService._snapshot_values(metric)
                snapshot = existing.get((current, metric.work_center_id))
                if snapshot is None:
                    snapshot = PerformanceSnapshot(
                        metric_date=current,
                        work_center_id=metric.work_center_id,
                        calculated_at=calculated_at,
                        **values,
                    )
                    snapshot.created_by = PerformanceService._operator_id()
                    db.add(snapshot)
                else:
                    for key, value in values.items():
                        setattr(snapshot, key, value)
                    snapshot.calculated_at = calculated_at
                    snapshot.updated_by = PerformanceService._operator_id()
                snapshot_count += 1
            current += timedelta(days=1)
        await db.flush()
        return SnapshotRebuildResult(
            start_date=obj.start_date,
            end_date=obj.end_date,
            work_center_count=len(context.centers),
            snapshot_count=snapshot_count,
        )

    @staticmethod
    async def snapshots(
        db: AsyncSession,
        start_date: date | None,
        end_date: date | None,
        work_center_id: int | None = None,
    ) -> list[PerformanceSnapshotDetail]:
        resolved_start, resolved_end, _, _ = resolve_period(start_date, end_date)
        stmt = (
            select(PerformanceSnapshot, WorkCenter)
            .join(WorkCenter, WorkCenter.id == PerformanceSnapshot.work_center_id)
            .where(
                PerformanceSnapshot.metric_date >= resolved_start,
                PerformanceSnapshot.metric_date <= resolved_end,
                PerformanceSnapshot.deleted == 0,
            )
        )
        if work_center_id:
            stmt = stmt.where(PerformanceSnapshot.work_center_id == work_center_id)
        rows = (
            await db.execute(
                stmt.order_by(
                    PerformanceSnapshot.metric_date.desc(), WorkCenter.work_center_code
                )
            )
        ).all()
        result: list[PerformanceSnapshotDetail] = []
        for snapshot, center in rows:
            detail = PerformanceSnapshotDetail.model_validate(snapshot)
            detail.work_center_code = center.work_center_code
            detail.work_center_name = center.work_center_name
            result.append(detail)
        return result


performance_service = PerformanceService()
