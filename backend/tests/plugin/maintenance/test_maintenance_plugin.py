from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.maintenance.api.v1.mes.maintenance import router
from backend.plugin.maintenance.enums import (
    CycleUnit,
    DowntimeCategory,
    MaintenancePlanType,
    TaskResult,
)
from backend.plugin.maintenance.model import (
    EquipmentDowntime,
    MaintenancePlan,
    MaintenanceTask,
    RepairCostPosting,
    RepairOrder,
    RepairPartIssue,
)
from backend.plugin.maintenance.schema.maintenance import (
    CompleteRepair,
    CreateDowntime,
    CreateMaintenancePlan,
    GenerateDueTasks,
)
from backend.plugin.maintenance.service.maintenance_service import (
    advance_cycle,
    duration_minutes,
    enum_value,
    is_due_for_generation,
)
from backend.utils.timezone import timezone


def test_maintenance_models_and_foreign_keys_registered() -> None:
    assert MaintenancePlan.__tablename__ == 'mes_maintenance_plan'
    assert MaintenanceTask.__tablename__ == 'mes_maintenance_task'
    assert RepairOrder.__tablename__ == 'mes_repair_order'
    assert RepairPartIssue.__tablename__ == 'mes_repair_part_issue'
    assert RepairCostPosting.__tablename__ == 'mes_repair_cost_posting'
    assert EquipmentDowntime.__tablename__ == 'mes_equipment_downtime'

    constraints = {
        constraint.name
        for model in (MaintenancePlan, EquipmentDowntime, MaintenanceTask, RepairOrder)
        for constraint in model.__table__.foreign_key_constraints
    }
    assert constraints == {
        'fk_maintenance_plan_equipment',
        'fk_maintenance_plan_center',
        'fk_maintenance_plan_user',
        'fk_equipment_downtime_equipment',
        'fk_equipment_downtime_center',
        'fk_maintenance_task_plan',
        'fk_maintenance_task_equipment',
        'fk_maintenance_task_center',
        'fk_maintenance_task_user',
        'fk_maintenance_task_downtime',
        'fk_repair_order_equipment',
        'fk_repair_order_center',
        'fk_repair_order_user',
        'fk_repair_order_downtime',
    }


def test_maintenance_route_surface() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}

    assert ('/dashboard', frozenset({'GET'})) in endpoints
    assert ('/plans', frozenset({'POST'})) in endpoints
    assert ('/plans/generate-due', frozenset({'POST'})) in endpoints
    assert ('/tasks/{task_id}/complete', frozenset({'POST'})) in endpoints
    assert ('/repairs/{repair_id}/assign', frozenset({'POST'})) in endpoints
    assert ('/repairs/{repair_id}/complete', frozenset({'POST'})) in endpoints
    assert ('/repairs/{repair_id}/parts', frozenset({'POST'})) in endpoints
    assert ('/repairs/{repair_id}/cost/post', frozenset({'POST'})) in endpoints
    assert ('/repairs/cost-analysis', frozenset({'GET'})) in endpoints
    assert ('/downtimes/{downtime_id}/close', frozenset({'POST'})) in endpoints
    assert len(router.routes) == 21


def test_plan_schema_normalizes_code_and_checklist() -> None:
    plan = CreateMaintenancePlan(
        plan_no=' pm-press-01 ',
        plan_name='  Press monthly maintenance  ',
        equipment_id=1,
        plan_type=MaintenancePlanType.PREVENTIVE,
        next_due_date=date(2026, 8, 31),
        checklist_items=[' Lubricate ', '', 'Check guard'],
    )

    assert plan.plan_no == 'PM-PRESS-01'
    assert plan.plan_name == 'Press monthly maintenance'
    assert plan.checklist_items == ['Lubricate', 'Check guard']


def test_cycle_advance_handles_month_end_and_leap_year() -> None:
    assert advance_cycle(date(2026, 1, 31), CycleUnit.MONTH, 1) == date(2026, 2, 28)
    assert advance_cycle(date(2024, 1, 31), CycleUnit.MONTH, 1) == date(2024, 2, 29)
    assert advance_cycle(date(2026, 8, 9), CycleUnit.WEEK, 2) == date(2026, 8, 23)
    assert advance_cycle(date(2026, 8, 9), CycleUnit.DAY, 10) == date(2026, 8, 19)


def test_plan_lead_days_control_generation_eligibility() -> None:
    assert is_due_for_generation(date(2026, 8, 20), 10, date(2026, 8, 10))
    assert not is_due_for_generation(date(2026, 8, 21), 10, date(2026, 8, 10))


def test_downtime_range_and_duration_rules() -> None:
    start_at = datetime(2026, 8, 10, 8)
    downtime = CreateDowntime(
        downtime_no=' dt-001 ',
        equipment_id=1,
        category=DowntimeCategory.PLANNED,
        start_at=start_at,
        end_at=datetime(2026, 8, 10, 9, 30),
    )

    assert downtime.downtime_no == 'DT-001'
    assert downtime.start_at.tzinfo == timezone.tz_info
    assert duration_minutes(downtime.start_at, downtime.end_at) == Decimal('90.0000')

    with pytest.raises(ValidationError):
        CreateDowntime(
            equipment_id=1,
            category=DowntimeCategory.UNPLANNED,
            start_at=start_at,
            end_at=start_at,
        )


def test_generation_and_repair_validation_limits() -> None:
    with pytest.raises(ValidationError):
        GenerateDueTasks(through_date=date(2026, 8, 31), max_tasks=5001)
    with pytest.raises(ValidationError):
        CompleteRepair(root_cause=' ', repair_action='Adjusted drive', repair_cost=Decimal('0'))

    completion = CompleteRepair(
        root_cause='Bearing wear',
        repair_action='Replace bearing',
        repair_cost=Decimal('123.4500'),
    )
    assert completion.repair_cost == Decimal('123.4500')


def test_task_result_values_match_api_contract() -> None:
    assert TaskResult.PASS == 'PASS'
    assert TaskResult.FAIL == 'FAIL'
    assert enum_value(MaintenancePlanType.PREVENTIVE) == 'PREVENTIVE'
    assert enum_value('PREVENTIVE') == 'PREVENTIVE'
