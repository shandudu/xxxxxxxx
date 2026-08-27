from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.plugin.routing.enums import RunTimeUnit
from backend.plugin.maintenance.enums import DowntimeCategory
from backend.plugin.scheduling.api.v1.mes.scheduling import router
from backend.plugin.scheduling.enums import SchedulingDirection
from backend.plugin.scheduling.model import (
    ApsDispatch,
    ApsOperationSchedule,
    ApsSchedule,
    CalendarDay,
    Shift,
    WorkCalendar,
    WorkCenterCalendar,
)
from backend.plugin.scheduling.schema.scheduling import CreateApsSchedule, CreateDispatch, CreateShift
from backend.plugin.scheduling.service.scheduling_service import CalendarResolver, calculate_operation_minutes
from backend.utils.timezone import timezone


def test_scheduling_models_registered() -> None:
    assert Shift.__tablename__ == 'mes_aps_shift'
    assert WorkCalendar.__tablename__ == 'mes_aps_calendar'
    assert CalendarDay.__tablename__ == 'mes_aps_calendar_day'
    assert WorkCenterCalendar.__tablename__ == 'mes_aps_work_center_calendar'
    assert ApsSchedule.__tablename__ == 'mes_aps_schedule'
    assert ApsOperationSchedule.__tablename__ == 'mes_aps_operation_schedule'
    assert ApsDispatch.__tablename__ == 'mes_aps_dispatch'


def test_scheduling_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '/shifts' in paths
    assert '/calendars/{calendar_id}/days' in paths
    assert '/calendars/{calendar_id}/work-centers' in paths
    assert '/work-orders/options' in paths
    assert '/schedules' in paths
    assert '/schedules/{schedule_id}/publish' in paths
    assert '/schedules/{schedule_id}/loads' in paths
    assert '/dispatches/{dispatch_id}/accept' in paths
    assert len(router.routes) == 19


def test_shift_and_schedule_validation() -> None:
    shift = CreateShift(
        shift_code='day-1',
        shift_name='Day shift',
        start_time=time(8),
        end_time=time(17),
        break_minutes=60,
    )
    assert shift.shift_code == 'DAY-1'
    with pytest.raises(ValidationError):
        CreateShift(
            shift_code='invalid',
            shift_name='Invalid',
            start_time=time(17),
            end_time=time(8),
        )
    start = datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    schedule = CreateApsSchedule(
        schedule_name='Week 33',
        direction=SchedulingDirection.FORWARD,
        horizon_start_at=start,
        horizon_end_at=start.replace(day=14, hour=18),
        work_order_ids=[1, 2],
    )
    assert schedule.work_order_ids == [1, 2]
    with pytest.raises(ValidationError):
        CreateApsSchedule(
            schedule_name='Duplicate orders',
            horizon_start_at=start,
            horizon_end_at=start.replace(day=14, hour=18),
            work_order_ids=[1, 1],
        )


def test_dispatch_requires_assignment() -> None:
    with pytest.raises(ValidationError):
        CreateDispatch(schedule_operation_id=1)
    obj = CreateDispatch(schedule_operation_id=1, assigned_team='Assembly A')
    assert obj.assigned_team == 'Assembly A'


@pytest.mark.parametrize(
    ('unit', 'expected'),
    [
        (RunTimeUnit.MIN_PER_BASE_QTY, Decimal('65.0000')),
        (RunTimeUnit.HOUR_PER_BASE_QTY, Decimal('3605.0000')),
        (RunTimeUnit.SEC_PER_BASE_QTY, Decimal('6.0000')),
    ],
)
def test_operation_time_calculation(unit: RunTimeUnit, expected: Decimal) -> None:
    operation = SimpleNamespace(
        setup_time_min=Decimal('5'),
        run_time_value=Decimal('60'),
        run_time_unit=unit,
        queue_time_min=Decimal('10'),
        move_time_min=Decimal('2'),
    )
    setup, run, queue, move = calculate_operation_minutes(
        quantity=Decimal('10'),
        base_quantity=Decimal('10'),
        routing_operation=operation,
    )
    assert setup + run == expected
    assert queue == Decimal('10.0000')
    assert move == Decimal('2.0000')


def test_default_calendar_skips_weekend() -> None:
    resolver = CalendarResolver(shifts={}, calendars={}, days={}, assignments={})
    saturday = datetime(2026, 8, 8, 9, tzinfo=timezone.tz_info)
    start, end = resolver.forward(1, saturday, Decimal('120'))
    assert start == datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    assert end == datetime(2026, 8, 10, 10, tzinfo=timezone.tz_info)


def test_default_calendar_backward_skips_weekend() -> None:
    resolver = CalendarResolver(shifts={}, calendars={}, days={}, assignments={})
    monday_before_shift = datetime(2026, 8, 10, 7, tzinfo=timezone.tz_info)
    start, end = resolver.backward(1, monday_before_shift, Decimal('120'))
    assert start == datetime(2026, 8, 7, 15, tzinfo=timezone.tz_info)
    assert end == datetime(2026, 8, 7, 17, tzinfo=timezone.tz_info)


def test_cross_midnight_shift_uses_previous_calendar_day() -> None:
    shift = SimpleNamespace(
        id=1,
        start_time=time(20),
        end_time=time(4),
        spans_next_day=True,
        break_minutes=0,
    )
    calendar = SimpleNamespace(id=1, weekday_mask='1,2,3,4,5,6,7', default_shift_id=1)
    assignment = SimpleNamespace(
        calendar_id=1,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        capacity_factor=Decimal('1'),
    )
    resolver = CalendarResolver(
        shifts={1: shift},
        calendars={1: calendar},
        days={},
        assignments={9: [assignment]},
    )
    early_monday = datetime(2026, 8, 10, 2, tzinfo=timezone.tz_info)
    start, end = resolver.forward(9, early_monday, Decimal('120'))
    assert start == early_monday
    assert end == datetime(2026, 8, 10, 4, tzinfo=timezone.tz_info)


def test_downtime_is_removed_from_capacity_window() -> None:
    monday = datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    resolver = CalendarResolver(
        shifts={},
        calendars={},
        days={},
        assignments={},
        downtimes={1: [(monday.replace(hour=9), monday.replace(hour=10))]},
    )
    start, end = resolver.forward(1, monday, Decimal('120'))
    assert start == monday
    assert end == monday.replace(hour=11)


def test_empty_downtime_category_filter_can_represent_raw_calendar() -> None:
    assert DowntimeCategory.PLANNED.value == 'PLANNED'
    resolver = CalendarResolver(
        shifts={},
        calendars={},
        days={},
        assignments={},
        downtimes={},
    )
    monday = datetime(2026, 8, 10, 8, tzinfo=timezone.tz_info)
    assert resolver.forward(1, monday, Decimal('60')) == (monday, monday.replace(hour=9))
