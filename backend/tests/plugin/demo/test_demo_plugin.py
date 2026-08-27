from backend.plugin.demo.api.v1.mes.demo import router
from backend.plugin.demo.enums import DemoRunStatus
from backend.plugin.demo.model import ManufacturingDemoRun
from backend.plugin.demo.schema.demo import ManufacturingDemoVerifyResult
from backend.plugin.demo.service.demo_service import (
    REFERENCES,
    SALES_ORDER_DRIVEN_REFERENCES,
    SALES_ORDER_DRIVEN_SCENARIO,
    SCENARIO,
)


def test_demo_model_and_scenario_contract() -> None:
    assert ManufacturingDemoRun.__tablename__ == 'mes_demo_run'
    assert SCENARIO == 'MANUFACTURING_HAPPY_PATH'
    assert SALES_ORDER_DRIVEN_SCENARIO == 'SALES_ORDER_DRIVEN_HAPPY_PATH'
    assert REFERENCES['finished_lot'] == 'DEMO-FG-LOT-001'
    assert SALES_ORDER_DRIVEN_REFERENCES['sales_order'] == 'DEMO-SOD-SO-001'
    assert DemoRunStatus.COMPLETED == 'COMPLETED'
    assert 'uk_mes_demo_run_scenario_deleted' in {
        constraint.name for constraint in ManufacturingDemoRun.__table__.constraints
    }


def test_demo_route_surface() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}
    assert endpoints == {
        ('/manufacturing-happy-path/run', frozenset({'POST'})),
        ('/manufacturing-happy-path/status', frozenset({'GET'})),
        ('/manufacturing-happy-path/verify', frozenset({'POST'})),
        ('/sales-order-driven-happy-path/run', frozenset({'POST'})),
        ('/sales-order-driven-happy-path/status', frozenset({'GET'})),
        ('/sales-order-driven-happy-path/verify', frozenset({'POST'})),
    }


def test_demo_verification_schema_defaults() -> None:
    result = ManufacturingDemoVerifyResult(passed=False)
    assert result.completed_steps == []
    assert result.missing_steps == []
    assert result.references == {}
