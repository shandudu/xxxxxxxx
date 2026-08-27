from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.operation_material.api.v1.mes.operation_material import router
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
from backend.plugin.operation_material.model import (
    OperationMaterialPlan,
    OperationMaterialRequirement,
)
from backend.plugin.operation_material.schema.operation_material import (
    CreateOperationMaterialPlan,
    CreateOperationMaterialRequirement,
)


def test_operation_material_models_registered() -> None:
    assert OperationMaterialPlan.__tablename__ == 'mes_operation_material_plan'
    assert OperationMaterialRequirement.__tablename__ == 'mes_operation_material_requirement'


def test_operation_material_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '' in paths
    assert '/{plan_id}/requirements' in paths
    assert '/{plan_id}/validate' in paths
    assert '/{plan_id}/activate' in paths
    assert '/{plan_id}/deactivate' in paths
    assert len(router.routes) == 10


def test_operation_material_schema_normalizes_code() -> None:
    plan = CreateOperationMaterialPlan(plan_code=' plan-001 ', bom_id=1, routing_id=2)
    assert plan.plan_code == 'PLAN-001'
    assert OperationMaterialPlanStatus.DRAFT == 'DRAFT'


def test_requirement_quantity_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        CreateOperationMaterialRequirement(
            bom_item_id=1,
            routing_operation_id=2,
            quantity=Decimal('0'),
        )
