from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.inventory.api.v1.mes.inventory import router
from backend.plugin.inventory.crud.inventory import inventory_repo
from backend.plugin.inventory.enums import StockMovementStatus, StockTransactionType
from backend.plugin.inventory.model import (
    InventoryBalance, InventoryPolicy, LotExpiryAlert, LotQualityHold, LotRecall,
    LotRecallItem, ReplenishmentSuggestion, ShelfLifePolicy, StockMovement,
    StockMovementLine, StockTransaction,
)
from backend.plugin.inventory.schema.inventory import CreateStockMovement, StockAdjustmentConfig, StockMovementLineConfig
from backend.plugin.inventory.schema.shelf_life import ShelfLifePolicyUpsert


def test_inventory_models_and_constraints_are_registered() -> None:
    assert InventoryBalance.__tablename__ == 'mes_inventory_balance'
    assert StockTransaction.__tablename__ == 'mes_stock_transaction'
    assert StockMovement.__tablename__ == 'mes_stock_movement'
    assert StockMovementLine.__tablename__ == 'mes_stock_movement_line'
    assert InventoryPolicy.__tablename__ == 'mes_inventory_policy'
    assert ReplenishmentSuggestion.__tablename__ == 'mes_replenishment_suggestion'
    assert ShelfLifePolicy.__tablename__ == 'mes_shelf_life_policy'
    assert LotExpiryAlert.__tablename__ == 'mes_lot_expiry_alert'
    assert LotQualityHold.__tablename__ == 'mes_lot_quality_hold'
    assert LotRecall.__tablename__ == 'mes_lot_recall'
    assert LotRecallItem.__tablename__ == 'mes_lot_recall_item'
    assert 'uk_mes_inventory_balance_key' in {constraint.name for constraint in InventoryBalance.__table__.constraints}
    assert 'uk_mes_stock_tx_idempotency' in {constraint.name for constraint in StockTransaction.__table__.constraints}


def test_inventory_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert {
        '/balances', '/transactions', '/movements', '/movements/{movement_id}',
        '/movements/{movement_id}/post', '/adjustments', '/policies', '/policies/{material_id}',
        '/replenishment/generate', '/replenishment', '/replenishment/dashboard',
        '/replenishment/{suggestion_id}/firm', '/replenishment/{suggestion_id}/release',
        '/shelf-life/dashboard', '/shelf-life/policies', '/shelf-life/policies/{material_id}',
        '/shelf-life/alerts/sync', '/shelf-life/alerts',
        '/shelf-life/alerts/{alert_id}/acknowledge', '/shelf-life/fefo-candidates',
        '/shelf-life/holds', '/shelf-life/holds/{hold_id}/reinspect',
        '/shelf-life/holds/{hold_id}/release', '/shelf-life/holds/{hold_id}/scrap',
        '/recalls', '/recalls/{recall_id}', '/recalls/{recall_id}/items/{item_id}',
        '/recalls/{recall_id}/close',
    } == paths


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


def test_shelf_life_policy_threshold_validation() -> None:
    policy = ShelfLifePolicyUpsert(warning_days=30, critical_days=7, min_remaining_days_at_issue=3)
    assert policy.fefo_enabled is True
    with pytest.raises(ValidationError):
        ShelfLifePolicyUpsert(warning_days=7, critical_days=30)
