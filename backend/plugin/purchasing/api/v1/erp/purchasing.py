from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.purchasing.schema.purchasing import ConfirmPurchaseOrder, CreatePurchaseOrder, CreateSupplierReceipt, PurchaseDeliveryDashboard, PurchaseDeliveryPerformanceDetail, PurchaseDeliveryRecalculateResult, PurchaseOrderDetail, SupplierReceiptDetail, SupplierReturnDetail
from backend.plugin.purchasing.service import purchasing_service, supplier_delivery_service


router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('erp:purchasing:view')), DependsRBAC]


@router.get('/orders', dependencies=view_dependencies)
async def list_orders(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> ResponseSchemaModel[list[PurchaseOrderDetail]]:
    return response_base.success(data=await purchasing_service.list_orders(db, supplier_id, status))


@router.post('/orders', dependencies=[Depends(RequestPermission('erp:purchasing:create')), DependsRBAC])
async def create_order(db: CurrentSessionTransaction, obj: CreatePurchaseOrder) -> ResponseSchemaModel[PurchaseOrderDetail]:
    return response_base.success(data=await purchasing_service.create_order(db, obj))


@router.get('/orders/{order_id}', dependencies=view_dependencies)
async def get_order(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[PurchaseOrderDetail]:
    return response_base.success(data=await purchasing_service.get_order(db, order_id))


@router.post('/orders/{order_id}/confirm', dependencies=[Depends(RequestPermission('erp:purchasing:confirm')), DependsRBAC])
async def confirm_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)], obj: ConfirmPurchaseOrder | None = None) -> ResponseSchemaModel[PurchaseOrderDetail]:
    return response_base.success(data=await purchasing_service.confirm_order(db, order_id, obj))


@router.post('/orders/{order_id}/cancel', dependencies=[Depends(RequestPermission('erp:purchasing:cancel')), DependsRBAC])
async def cancel_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[PurchaseOrderDetail]:
    return response_base.success(data=await purchasing_service.cancel_order(db, order_id))


@router.get('/receipts', dependencies=view_dependencies)
async def list_receipts(db: CurrentSession, order_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[SupplierReceiptDetail]]:
    return response_base.success(data=await purchasing_service.list_receipts(db, order_id))


@router.get('/delivery/dashboard', dependencies=view_dependencies)
async def delivery_dashboard(db: CurrentSession) -> ResponseSchemaModel[PurchaseDeliveryDashboard]:
    return response_base.success(data=await supplier_delivery_service.dashboard(db))


@router.post('/delivery/recalculate', dependencies=[Depends(RequestPermission('erp:purchasing:confirm')), DependsRBAC])
async def recalculate_delivery(db: CurrentSessionTransaction) -> ResponseSchemaModel[PurchaseDeliveryRecalculateResult]:
    return response_base.success(data=await supplier_delivery_service.recalculate(db))


@router.get('/orders/{order_id}/delivery-performance', dependencies=view_dependencies)
async def order_delivery_performance(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[PurchaseDeliveryPerformanceDetail]]:
    return response_base.success(data=await supplier_delivery_service.list_order_performance(db, order_id))


@router.post('/receipts', dependencies=[Depends(RequestPermission('erp:purchasing:receipt')), DependsRBAC])
async def create_receipt(db: CurrentSessionTransaction, obj: CreateSupplierReceipt) -> ResponseSchemaModel[SupplierReceiptDetail]:
    return response_base.success(data=await purchasing_service.create_receipt(db, obj))


@router.get('/receipts/{receipt_id}', dependencies=view_dependencies)
async def get_receipt(db: CurrentSession, receipt_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[SupplierReceiptDetail]:
    return response_base.success(data=await purchasing_service.get_receipt(db, receipt_id))


@router.get('/returns', dependencies=view_dependencies)
async def list_returns(db: CurrentSession, supplier_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[SupplierReturnDetail]]:
    return response_base.success(data=await purchasing_service.list_returns(db, supplier_id))
