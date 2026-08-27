from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.common.exception import errors
from backend.plugin.maintenance.enums import DowntimeCategory
from backend.plugin.performance.api.v1.mes.performance import router
from backend.plugin.performance.enums import MetricGrain
from backend.plugin.performance.model import PerformanceSnapshot, PerformanceTarget
from backend.plugin.performance.schema.performance import (
    PerformanceTargetDetail,
    PerformanceTargetInput,
    RebuildSnapshots,
)
from backend.plugin.performance.service.performance_service import (
    AnalysisContext,
    DowntimeFact,
    ExecutionFact,
    PerformanceService,
    bucket_ranges,
    merged_interval_minutes,
    overlap_minutes,
    ratio_percent,
    resolve_period,
    standard_run_minutes,
)
from backend.plugin.routing.enums import RunTimeUnit
from backend.utils.timezone import timezone


def test_performance_models_and_foreign_keys_registered() -> None:
    assert PerformanceTarget.__tablename__ == 'mes_performance_target'
    assert PerformanceSnapshot.__tablename__ == 'mes_performance_snapshot'
    constraints = {
        constraint.name
        for model in (PerformanceTarget, PerformanceSnapshot)
        for constraint in model.__table__.foreign_key_constraints
    }
    assert constraints == {
        'fk_performance_target_center',
        'fk_performance_snapshot_center',
    }


def test_performance_route_surface() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}
    assert ('/dashboard', frozenset({'GET'})) in endpoints
    assert ('/work-centers', frozenset({'GET'})) in endpoints
    assert ('/trend', frozenset({'GET'})) in endpoints
    assert ('/equipment-reliability', frozenset({'GET'})) in endpoints
    assert ('/cycle-analysis', frozenset({'GET'})) in endpoints
    assert ('/downtime-pareto', frozenset({'GET'})) in endpoints
    assert ('/targets/{work_center_id}', frozenset({'PUT'})) in endpoints
    assert ('/snapshots/rebuild', frozenset({'POST'})) in endpoints
    assert len(router.routes) == 10


@pytest.mark.parametrize(
    ('unit', 'expected'),
    [
        (RunTimeUnit.MIN_PER_BASE_QTY, Decimal('30.0000')),
        (RunTimeUnit.HOUR_PER_BASE_QTY, Decimal('1800.0000')),
        (RunTimeUnit.SEC_PER_BASE_QTY, Decimal('0.5000')),
    ],
)
def test_standard_run_minutes_supports_all_routing_units(
    unit: RunTimeUnit, expected: Decimal
) -> None:
    assert standard_run_minutes(Decimal('50'), Decimal('60'), unit, Decimal('100')) == expected


def test_ratio_percent_handles_zero_and_capacity_overrun() -> None:
    assert ratio_percent(Decimal('9'), Decimal('10')) == Decimal('90.0000')
    assert ratio_percent(Decimal('2'), Decimal('0')) == Decimal('0.0000')
    assert ratio_percent(Decimal('12'), Decimal('10')) == Decimal('100.0000')
    assert ratio_percent(Decimal('12'), Decimal('10'), cap=False) == Decimal('120.0000')


def test_overlap_and_merged_intervals_do_not_double_count() -> None:
    period_start = datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    period_end = period_start + timedelta(hours=8)
    assert overlap_minutes(
        period_start - timedelta(hours=1),
        period_start + timedelta(hours=1),
        period_start,
        period_end,
    ) == Decimal('60.0000')
    assert merged_interval_minutes(
        [
            (period_start, period_start + timedelta(hours=2)),
            (period_start + timedelta(hours=1), period_start + timedelta(hours=3)),
            (period_start + timedelta(hours=4), period_start + timedelta(hours=5)),
        ],
        period_start,
        period_end,
    ) == Decimal('240.0000')


def test_period_and_bucket_validation() -> None:
    start, end, start_at, end_at = resolve_period(
        date(2026, 8, 1), date(2026, 8, 10)
    )
    assert (start, end) == (date(2026, 8, 1), date(2026, 8, 10))
    assert end_at - start_at == timedelta(days=10)
    assert bucket_ranges(start, end, MetricGrain.WEEK) == [
        (date(2026, 8, 1), date(2026, 8, 7)),
        (date(2026, 8, 8), date(2026, 8, 10)),
    ]
    with pytest.raises(errors.RequestError):
        resolve_period(date(2026, 8, 10), date(2026, 8, 1))


def test_target_and_snapshot_rebuild_schema_rules() -> None:
    detail = PerformanceTargetDetail(work_center_id=1)
    assert detail.work_center_code == ''
    assert detail.oee_target == Decimal('85')
    with pytest.raises(ValidationError):
        PerformanceTargetInput(oee_target=Decimal('101'))
    with pytest.raises(ValidationError):
        RebuildSnapshots(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            work_center_ids=[1, 1],
        )
    with pytest.raises(ValidationError):
        RebuildSnapshots(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 4, 5),
        )


class _FixedCalendar:
    def __init__(self, minutes: Decimal) -> None:
        self.minutes = minutes

    def available_minutes(self, center: object, start_at: datetime, end_at: datetime) -> Decimal:
        return self.minutes


def test_center_oee_reliability_cycle_and_capacity_formula() -> None:
    start_at = datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    end_at = start_at + timedelta(hours=8)
    center = SimpleNamespace(
        id=1,
        work_center_code='WC-01',
        work_center_name='Assembly',
        parallel_capacity=1,
    )
    execution = ExecutionFact(
        execution_id=1,
        work_center_id=1,
        operation_id=10,
        operation_code='OP-10',
        operation_name='Assembly',
        product_code='FG-01',
        product_name='Finished good',
        started_at=start_at,
        completed_at=start_at + timedelta(hours=5),
        good_quantity=Decimal('90'),
        scrap_quantity=Decimal('10'),
        ideal_run_minutes=Decimal('180'),
    )
    downtime = DowntimeFact(
        downtime_id=1,
        equipment_id=1,
        work_center_id=1,
        category=DowntimeCategory.UNPLANNED.value,
        start_at=start_at + timedelta(hours=6),
        end_at=start_at + timedelta(hours=7),
        reason='Bearing failure',
    )
    context = AnalysisContext(
        centers=[center],
        equipment=[],
        targets={},
        executions=[execution],
        downtimes=[downtime],
        raw_calendar=_FixedCalendar(Decimal('480')),
        planned_calendar=_FixedCalendar(Decimal('420')),
        operating_calendar=_FixedCalendar(Decimal('360')),
        start_at=start_at,
        end_at=end_at,
    )

    result = PerformanceService._center_metric(context, center, start_at, end_at)

    assert result.planned_downtime_minutes == Decimal('60.0000')
    assert result.unplanned_downtime_minutes == Decimal('60.0000')
    assert result.availability_rate == Decimal('85.7143')
    assert result.performance_rate == Decimal('50.0000')
    assert result.quality_rate == Decimal('90.0000')
    assert result.oee_rate == Decimal('38.5714')
    assert result.utilization_rate == Decimal('83.3333')
    assert result.actual_cycle_seconds == Decimal('180.000000')
    assert result.ideal_cycle_seconds == Decimal('108.000000')
    assert result.failure_count == 1
    assert result.mtbf_minutes == Decimal('360.0000')
    assert result.mttr_minutes == Decimal('60.0000')
