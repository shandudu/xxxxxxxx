from typing import Annotated
from decimal import Decimal

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.inventory.schema.inventory import (
    CreateStockMovement, GenerateReplenishment, InventoryBalanceDetail, InventoryPolicyDetail, InventoryPolicyUpsert, ReleaseReplenishment, ReplenishmentDashboard, ReplenishmentSuggestionDetail, StockAdjustmentConfig, StockMovementDetail, StockTransactionDetail,
)
from backend.plugin.inventory.schema.shelf_life import (
    CreateLotRecall,
    ExpiryAlertDetail,
    FefoCandidateDetail,
    LotHoldDetail,
    LotRecallDetail,
    RecallItemDetail,
    ReleaseLotHold,
    ScrapLotHold,
    ShelfLifeDashboard,
    ShelfLifePolicyDetail,
    ShelfLifePolicyUpsert,
    UpdateRecallItem,
)
from backend.plugin.inventory.service import inventory_service, replenishment_service, shelf_life_service


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


@router.get('/shelf-life/dashboard', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def shelf_life_dashboard(db: CurrentSession) -> ResponseSchemaModel[ShelfLifeDashboard]:
    return response_base.success(data=await shelf_life_service.dashboard(db))


@router.get('/shelf-life/policies', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def list_shelf_life_policies(db: CurrentSession) -> ResponseSchemaModel[list[ShelfLifePolicyDetail]]:
    return response_base.success(data=await shelf_life_service.list_policies(db))


@router.put('/shelf-life/policies/{material_id}', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:config')), DependsRBAC])
async def upsert_shelf_life_policy(db: CurrentSessionTransaction, material_id: Annotated[int, Path(ge=1)], obj: ShelfLifePolicyUpsert) -> ResponseSchemaModel[ShelfLifePolicyDetail]:
    return response_base.success(data=await shelf_life_service.upsert_policy(db, material_id, obj))


@router.post('/shelf-life/alerts/sync', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:execute')), DependsRBAC])
async def sync_shelf_life_alerts(db: CurrentSessionTransaction) -> ResponseSchemaModel[list[ExpiryAlertDetail]]:
    return response_base.success(data=await shelf_life_service.sync_expiry_alerts(db))


@router.get('/shelf-life/alerts', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def list_shelf_life_alerts(db: CurrentSession, status: Annotated[str | None, Query(max_length=20)] = None, level: Annotated[str | None, Query(max_length=20)] = None) -> ResponseSchemaModel[list[ExpiryAlertDetail]]:
    return response_base.success(data=await shelf_life_service.list_alerts(db, status, level))


@router.post('/shelf-life/alerts/{alert_id}/acknowledge', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:execute')), DependsRBAC])
async def acknowledge_shelf_life_alert(db: CurrentSessionTransaction, alert_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ExpiryAlertDetail]:
    return response_base.success(data=await shelf_life_service.acknowledge_alert(db, alert_id))


@router.get('/shelf-life/fefo-candidates', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def fefo_candidates(db: CurrentSession, material_id: Annotated[int, Query(ge=1)], warehouse_id: Annotated[int, Query(ge=1)], quantity: Annotated[Decimal, Query(gt=0)]) -> ResponseSchemaModel[list[FefoCandidateDetail]]:
    return response_base.success(data=await shelf_life_service.fefo_candidates(db, material_id=material_id, warehouse_id=warehouse_id, quantity=quantity))


@router.get('/shelf-life/holds', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def list_lot_holds(db: CurrentSession, status: Annotated[str | None, Query(max_length=30)] = None) -> ResponseSchemaModel[list[LotHoldDetail]]:
    return response_base.success(data=await shelf_life_service.list_holds(db, status))


@router.post('/shelf-life/holds/{hold_id}/reinspect', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:execute')), DependsRBAC])
async def create_hold_reinspection(db: CurrentSessionTransaction, hold_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[LotHoldDetail]:
    return response_base.success(data=await shelf_life_service.create_reinspection(db, hold_id))


@router.post('/shelf-life/holds/{hold_id}/release', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:execute')), DependsRBAC])
async def release_lot_hold(db: CurrentSessionTransaction, hold_id: Annotated[int, Path(ge=1)], obj: ReleaseLotHold) -> ResponseSchemaModel[LotHoldDetail]:
    return response_base.success(data=await shelf_life_service.release_hold(db, hold_id, obj))


@router.post('/shelf-life/holds/{hold_id}/scrap', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:execute')), DependsRBAC])
async def scrap_lot_hold(db: CurrentSessionTransaction, hold_id: Annotated[int, Path(ge=1)], obj: ScrapLotHold) -> ResponseSchemaModel[LotHoldDetail]:
    return response_base.success(data=await shelf_life_service.scrap_hold(db, hold_id, obj))


@router.get('/recalls', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def list_lot_recalls(db: CurrentSession, status: Annotated[str | None, Query(max_length=20)] = None) -> ResponseSchemaModel[list[LotRecallDetail]]:
    return response_base.success(data=await shelf_life_service.list_recalls(db, status))


@router.post('/recalls', dependencies=[Depends(RequestPermission('mes:inventory:recall')), DependsRBAC])
async def create_lot_recall(db: CurrentSessionTransaction, obj: CreateLotRecall) -> ResponseSchemaModel[LotRecallDetail]:
    return response_base.success(data=await shelf_life_service.create_recall(db, obj))


@router.get('/recalls/{recall_id}', dependencies=[Depends(RequestPermission('mes:inventory:shelf-life:view')), DependsRBAC])
async def get_lot_recall(db: CurrentSession, recall_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[LotRecallDetail]:
    return response_base.success(data=await shelf_life_service.get_recall(db, recall_id))


@router.put('/recalls/{recall_id}/items/{item_id}', dependencies=[Depends(RequestPermission('mes:inventory:recall')), DependsRBAC])
async def update_lot_recall_item(db: CurrentSessionTransaction, recall_id: Annotated[int, Path(ge=1)], item_id: Annotated[int, Path(ge=1)], obj: UpdateRecallItem) -> ResponseSchemaModel[RecallItemDetail]:
    return response_base.success(data=await shelf_life_service.update_recall_item(db, recall_id, item_id, obj))


@router.post('/recalls/{recall_id}/close', dependencies=[Depends(RequestPermission('mes:inventory:recall')), DependsRBAC])
async def close_lot_recall(db: CurrentSessionTransaction, recall_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[LotRecallDetail]:
    return response_base.success(data=await shelf_life_service.close_recall(db, recall_id))
