from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.production.api.v1.mes.production import router
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import MaterialConsumption, MaterialIssue, MaterialReturn, ProductionAndonAction, ProductionAndonAssignment, ProductionAndonEvent, ProductionExecution, ProductionReport, WorkOrder, WorkOrderMaterialAllocation, WorkOrderMaterialRequirement
from backend.plugin.production.schema.execution import CompleteProductionExecution
from backend.plugin.production.schema.production import CreateMaterialIssue, CreateProductionReport, CreateWorkOrder


def test_production_models_registered() -> None:
    assert WorkOrder.__tablename__ == 'mes_work_order'
    assert WorkOrderMaterialRequirement.__tablename__ == 'mes_work_order_material_requirement'
    assert MaterialIssue.__tablename__ == 'mes_material_issue'
    assert MaterialReturn.__tablename__ == 'mes_material_return'
    assert ProductionReport.__tablename__ == 'mes_production_report'
    assert ProductionExecution.__tablename__ == 'mes_production_execution'
    assert MaterialConsumption.__tablename__ == 'mes_material_consumption'
    assert WorkOrderMaterialAllocation.__tablename__ == 'mes_work_order_material_allocation'
    assert ProductionAndonEvent.__tablename__ == 'mes_production_andon_event'
    assert ProductionAndonAssignment.__tablename__ == 'mes_production_andon_assignment'
    assert ProductionAndonAction.__tablename__ == 'mes_production_andon_action'


def test_production_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '/work-orders' in paths
    assert '/work-orders/{order_id}/release' in paths
    assert '/material-issues' in paths
    assert '/material-returns' in paths
    assert '/reports' in paths
    assert len(router.routes) == 28
    assert '/dashboard' in paths
    assert '/work-orders/{order_id}/material-variance' in paths
    assert '/work-orders/{order_id}/executions' in paths
    assert '/work-orders/{order_id}/operations/{operation_id}/executions/start' in paths
    assert '/executions/{execution_id}/consumptions' in paths
    assert '/executions/{execution_id}/complete' in paths
    assert '/andon/dashboard' in paths
    assert '/andon/events/{event_id}/resolve' in paths


def test_work_order_and_report_schema() -> None:
    order = CreateWorkOrder(product_material_id=1, bom_id=2, routing_id=3, planned_quantity=Decimal('10'))
    assert order.planned_quantity == Decimal('10')
    assert WorkOrderStatus.IN_PROGRESS == 'IN_PROGRESS'
    report = CreateProductionReport(
        work_order_id=1, good_quantity=Decimal('2.5'), warehouse_id=1, location_id=2,
    )
    assert report.scrap_quantity == Decimal('0')


def test_issue_requires_at_least_one_line() -> None:
    with pytest.raises(ValidationError):
        CreateMaterialIssue(work_order_id=1, lines=[])


def test_execution_completion_requires_positive_total() -> None:
    with pytest.raises(ValidationError):
        CompleteProductionExecution(good_quantity=Decimal('0'), scrap_quantity=Decimal('0'))
