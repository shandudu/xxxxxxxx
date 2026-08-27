from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.inventory.schema.inventory import (
    CreateStockMovement, GenerateReplenishment, InventoryBalanceDetail, InventoryPolicyDetail, InventoryPolicyUpsert, ReleaseReplenishment, ReplenishmentDashboard, ReplenishmentSuggestionDetail, StockAdjustmentConfig, StockMovementDetail, StockTransactionDetail,
)
from backend.plugin.inventory.service import inventory_service, replenishment_service


router = APIRouter()


@router.get('/balances', dependencies=[DependsJwtAuth])
async def list_balances(
    db: CurrentSession,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    warehouse_id: Annotated[int | None, Query(ge=1)] = None,
    location_id: Annotated[int | None, Query(ge=1)] = None,
    lot_id: Annotated[int | None, Query(ge=1)] = None,
    positive_only: Annotated[bool, Query()] = False,
) -> ResponseSchemaModel[list[InventoryBalanceDetail]]:
    data = await inventory_service.list_balances(
        db, material_id=material_id, warehouse_id=warehouse_id, location_id=location_id,
        lot_id=lot_id, positive_only=positive_only,
    )
    return response_base.success(data=data)


@router.get('/transactions', dependencies=[DependsJwtAuth])
async def list_transactions(
    db: CurrentSession,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    lot_id: Annotated[int | None, Query(ge=1)] = None,
    reference_type: Annotated[str | None, Query(max_length=50)] = None,
    reference_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> ResponseSchemaModel[list[StockTransactionDetail]]:
    data = await inventory_service.list_transactions(
        db, material_id=material_id, lot_id=lot_id, reference_type=reference_type,
        reference_id=reference_id, limit=limit,
    )
    return response_base.success(data=data)


@router.post('/movements', dependencies=[Depends(RequestPermission('mes:inventory:movement:create')), DependsRBAC])
async def create_movement(db: CurrentSessionTransaction, obj: CreateStockMovement) -> ResponseSchemaModel[StockMovementDetail]:
    return response_base.success(data=await inventory_service.create_movement(db, obj))


@router.get('/movements', dependencies=[DependsJwtAuth])
async def list_movements(db: CurrentSession, status: Annotated[str | None, Query(max_length=20)] = None) -> ResponseSchemaModel[list[StockMovementDetail]]:
    return response_base.success(data=await inventory_service.list_movements(db, status))


@router.get('/movements/{movement_id}', dependencies=[DependsJwtAuth])
async def get_movement(db: CurrentSession, movement_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[StockMovementDetail]:
    return response_base.success(data=await inventory_service.get_movement(db, movement_id))


@router.post('/movements/{movement_id}/post', dependencies=[Depends(RequestPermission('mes:inventory:movement:post')), DependsRBAC])
async def post_movement(db: CurrentSessionTransaction, movement_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[StockMovementDetail]:
    return response_base.success(data=await inventory_service.post_movement(db, movement_id))


@router.post('/adjustments', dependencies=[Depends(RequestPermission('mes:inventory:adjustment')), DependsRBAC])
async def post_adjustment(db: CurrentSessionTransaction, obj: StockAdjustmentConfig) -> ResponseSchemaModel[StockTransactionDetail]:
    return response_base.success(data=await inventory_service.post_adjustment(db, obj))


@router.get('/policies', dependencies=[DependsJwtAuth])
async def list_inventory_policies(db: CurrentSession) -> ResponseSchemaModel[list[InventoryPolicyDetail]]:
    return response_base.success(data=await replenishment_service.list_policies(db))


@router.put('/policies/{material_id}', dependencies=[Depends(RequestPermission('mes:inventory:policy')), DependsRBAC])
async def upsert_inventory_policy(db: CurrentSessionTransaction, material_id: Annotated[int, Path(ge=1)], obj: InventoryPolicyUpsert) -> ResponseSchemaModel[InventoryPolicyDetail]:
    return response_base.success(data=await replenishment_service.upsert_policy(db, material_id, obj))


@router.post('/replenishment/generate', dependencies=[Depends(RequestPermission('mes:inventory:replenishment')), DependsRBAC])
async def generate_replenishment(db: CurrentSessionTransaction, obj: GenerateReplenishment) -> ResponseSchemaModel[list[ReplenishmentSuggestionDetail]]:
    return response_base.success(data=await replenishment_service.generate(db, obj))


@router.get('/replenishment', dependencies=[DependsJwtAuth])
async def list_replenishment(db: CurrentSession, status: Annotated[str | None, Query(max_length=20)] = None) -> ResponseSchemaModel[list[ReplenishmentSuggestionDetail]]:
    return response_base.success(data=await replenishment_service.list_suggestions(db, status))


@router.get('/replenishment/dashboard', dependencies=[DependsJwtAuth])
async def replenishment_dashboard(db: CurrentSession) -> ResponseSchemaModel[ReplenishmentDashboard]:
    return response_base.success(data=await replenishment_service.dashboard(db))


@router.post('/replenishment/{suggestion_id}/firm', dependencies=[Depends(RequestPermission('mes:inventory:replenishment')), DependsRBAC])
async def firm_replenishment(db: CurrentSessionTransaction, suggestion_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ReplenishmentSuggestionDetail]:
    return response_base.success(data=await replenishment_service.firm(db, suggestion_id))


@router.post('/replenishment/{suggestion_id}/release', dependencies=[Depends(RequestPermission('mes:inventory:replenishment')), DependsRBAC])
async def release_replenishment(db: CurrentSessionTransaction, suggestion_id: Annotated[int, Path(ge=1)], obj: ReleaseReplenishment) -> ResponseSchemaModel[ReplenishmentSuggestionDetail]:
    return response_base.success(data=await replenishment_service.release(db, suggestion_id, obj))
