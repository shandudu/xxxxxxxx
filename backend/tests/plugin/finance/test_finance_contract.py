from datetime import date
from decimal import Decimal

import pytest

from backend.plugin.finance.api.v1.erp.finance import router
from backend.plugin.finance.schema.finance import FinancePeriodCreate
from backend.plugin.finance.service.finance_service import money


def test_finance_router_exposes_valuation_settlement_voucher_and_dashboard() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}
    assert ('/inventory/valuation/calculate', frozenset({'POST'})) in endpoints
    assert ('/ar/invoices', frozenset({'POST'})) in endpoints
    assert ('/ap/payments', frozenset({'POST'})) in endpoints
    assert ('/vouchers/generate', frozenset({'POST'})) in endpoints
    assert ('/dashboard', frozenset({'GET'})) in endpoints


def test_finance_period_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError):
        FinancePeriodCreate(period_code='2026-08', start_date=date(2026, 8, 31), end_date=date(2026, 8, 1))


def test_finance_money_rounding_is_deterministic() -> None:
    assert money(Decimal('2.1234567')) == Decimal('2.123457')
