from datetime import date
from decimal import Decimal

import pytest

from backend.plugin.costing.api.v1.erp.costing import router
from backend.plugin.costing.schema.costing import CostPeriodCreate
from backend.plugin.costing.service.costing_service import money


def test_costing_router_exposes_period_settlement_and_margin_contract() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}
    assert ('/periods', frozenset({'GET'})) in endpoints
    assert ('/periods', frozenset({'POST'})) in endpoints
    assert ('/work-orders/{work_order_id}/calculate', frozenset({'POST'})) in endpoints
    assert ('/work-orders/{work_order_id}/post', frozenset({'POST'})) in endpoints
    assert ('/margins', frozenset({'GET'})) in endpoints


def test_cost_period_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError):
        CostPeriodCreate(period_code='2026-08', start_date=date(2026, 8, 31), end_date=date(2026, 8, 1))


def test_cost_money_is_quantized_for_reconciliation() -> None:
    assert money(Decimal('1.23456789')) == Decimal('1.234568')
