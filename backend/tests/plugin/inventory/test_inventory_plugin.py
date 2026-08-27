from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.inventory.api.v1.mes.inventory import router
from backend.plugin.inventory.crud.inventory import inventory_repo
from backend.plugin.inventory.enums import StockMovementStatus, StockTransactionType
from backend.plugin.inventory.model import InventoryBalance, InventoryPolicy, ReplenishmentSuggestion, StockMovement, StockMovementLine, StockTransaction
from backend.plugin.inventory.schema.inventory import CreateStockMovement, StockAdjustmentConfig, StockMovementLineConfig


def test_inventory_models_and_constraints_are_registered() -> None:
    assert InventoryBalance.__tablename__ == 'mes_inventory_balance'
    assert StockTransaction.__tablename__ == 'mes_stock_transaction'
    assert StockMovement.__tablename__ == 'mes_stock_movement'
    assert StockMovementLine.__tablename__ == 'mes_stock_movement_line'
    assert InventoryPolicy.__tablename__ == 'mes_inventory_policy'
    assert ReplenishmentSuggestion.__tablename__ == 'mes_replenishment_suggestion'
    assert 'uk_mes_inventory_balance_key' in {constraint.name for constraint in InventoryBalance.__table__.constraints}
    assert 'uk_mes_stock_tx_idempotency' in {constraint.name for constraint in StockTransaction.__table__.constraints}


def test_inventory_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert paths == {
        '/balances', '/transactions', '/movements', '/movements/{movement_id}',
        '/movements/{movement_id}/post', '/adjustments', '/policies', '/policies/{material_id}',
        '/replenishment/generate', '/replenishment', '/replenishment/dashboard',
        '/replenishment/{suggestion_id}/firm', '/replenishment/{suggestion_id}/release',
    }


def test_balance_key_handles_non_lot_inventory() -> None:
    assert inventory_repo.balance_key(1, None, 2, 3) == '1:0:2:3'
    assert inventory_repo.balance_key(1, 9, 2, 3) == '1:9:2:3'


def test_movement_schema_rejects_same_location() -> None:
    with pytest.raises(ValidationError):
        StockMovementLineConfig(
            material_id=1, from_warehouse_id=1, from_location_id=2,
            to_warehouse_id=1, to_location_id=2, quantity=Decimal('1'),
        )


def test_movement_and_adjustment_schema_validation() -> None:
    line = StockMovementLineConfig(
        material_id=1, lot_id=2, from_warehouse_id=1, from_location_id=3,
        to_warehouse_id=2, to_location_id=4, quantity=Decimal('1.25'),
    )
    movement = CreateStockMovement(lines=[line])
    assert movement.lines[0].quantity == Decimal('1.25')
    assert StockMovementStatus.DRAFT == 'DRAFT'
    assert StockTransactionType.TRANSFER_OUT == 'TRANSFER_OUT'
    with pytest.raises(ValidationError):
        StockAdjustmentConfig(
            idempotency_key='x', material_id=1, warehouse_id=1, location_id=1,
            quantity_delta=Decimal('0'),
        )
