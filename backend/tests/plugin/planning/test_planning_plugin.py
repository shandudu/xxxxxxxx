from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.planning.api.v1.mes.planning import router
from backend.plugin.planning.enums import MpsPlanStatus, PlannedOrderStatus, PlannedOrderType
from backend.plugin.planning.model import MpsDemand, MpsPlan, MrpRequirement, MrpRun, PlannedOrder
from backend.plugin.planning.schema.planning import CreateMpsDemand, CreateMpsPlan, CreateMrpRun
from backend.plugin.planning.service.planning_service import SupplyBucket, allocate_supply


def test_planning_models_registered() -> None:
    assert MpsPlan.__tablename__ == 'mes_mps_plan'
    assert MpsDemand.__tablename__ == 'mes_mps_demand'
    assert MrpRun.__tablename__ == 'mes_mrp_run'
    assert MrpRequirement.__tablename__ == 'mes_mrp_requirement'
    assert PlannedOrder.__tablename__ == 'mes_planned_order'


def test_planning_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '/mps-plans' in paths
    assert '/mps-plans/{plan_id}/demands' in paths
    assert '/mps-plans/{plan_id}/import-sales-orders' in paths
    assert '/mps-plans/{plan_id}/confirm' in paths
    assert '/mrp-runs' in paths
    assert '/mrp-runs/{run_id}' in paths
    assert '/planned-orders/{planned_order_id}/firm' in paths
    assert '/planned-orders/{planned_order_id}/release' in paths
    assert len(router.routes) == 12


def test_planning_schema_rules() -> None:
    plan = CreateMpsPlan(
        plan_name='August plan',
        horizon_start=date(2026, 8, 1),
        horizon_end=date(2026, 8, 31),
    )
    assert plan.plan_name == 'August plan'
    assert MpsPlanStatus.DRAFT == 'DRAFT'
    demand = CreateMpsDemand(
        material_id=1,
        demand_date=date(2026, 8, 20),
        quantity=Decimal('12.5'),
    )
    assert demand.quantity == Decimal('12.5')
    run = CreateMrpRun(mps_plan_id=1)
    assert run.default_purchase_lead_days == 7
    assert PlannedOrderType.PRODUCTION == 'PRODUCTION'
    assert PlannedOrderStatus.FIRM == 'FIRM'


def test_invalid_mps_horizon_and_quantity() -> None:
    with pytest.raises(ValidationError):
        CreateMpsPlan(
            plan_name='Invalid',
            horizon_start=date(2026, 9, 1),
            horizon_end=date(2026, 8, 1),
        )
    with pytest.raises(ValidationError):
        CreateMpsDemand(
            material_id=1,
            demand_date=date(2026, 8, 20),
            quantity=Decimal('0'),
        )


def test_supply_allocation_priority_and_residual_state() -> None:
    supply = SupplyBucket(
        on_hand=Decimal('3'),
        open_purchase=Decimal('4'),
        open_production=Decimal('5'),
    )
    allocated = allocate_supply(Decimal('10'), supply)
    assert allocated == (Decimal('3'), Decimal('4'), Decimal('3'), Decimal('0'))
    assert supply.on_hand == Decimal('0')
    assert supply.open_purchase == Decimal('0')
    assert supply.open_production == Decimal('2')


def test_supply_allocation_reports_net_requirement() -> None:
    supply = SupplyBucket(on_hand=Decimal('2'))
    allocated = allocate_supply(Decimal('7'), supply)
    assert allocated == (Decimal('2'), Decimal('0'), Decimal('0'), Decimal('5'))
