from typing import Annotated
from fastapi import APIRouter,Depends,Path,Query
from backend.common.response.response_schema import ResponseSchemaModel,response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession,CurrentSessionTransaction
from backend.plugin.sales.schema.sales import CreateSalesOrder,CreateShipment,DeliverShipment,DeliveryDashboard,DeliveryPerformanceDetail,DeliveryRecalculateResult,PromiseAssessmentDetail,PromiseDashboard,PromiseRecalculateResult,SalesOrderDetail,ShipmentDetail
from backend.plugin.sales.service import delivery_service,promise_service,sales_service
router=APIRouter();view=[DependsJwtAuth,Depends(RequestPermission('erp:sales:view')),DependsRBAC]
@router.get('/promise/dashboard',dependencies=view)
async def promise_dashboard(db:CurrentSession)->ResponseSchemaModel[PromiseDashboard]:return response_base.success(data=await promise_service.dashboard(db))
@router.post('/promise/recalculate',dependencies=[Depends(RequestPermission('erp:sales:confirm')),DependsRBAC])
async def recalculate_open_order_promises(db:CurrentSessionTransaction)->ResponseSchemaModel[PromiseRecalculateResult]:return response_base.success(data=await promise_service.recalculate_open_orders(db))
@router.get('/delivery/dashboard',dependencies=view)
async def delivery_dashboard(db:CurrentSession)->ResponseSchemaModel[DeliveryDashboard]:return response_base.success(data=await delivery_service.dashboard(db))
@router.post('/delivery/recalculate',dependencies=[Depends(RequestPermission('erp:sales:confirm')),DependsRBAC])
async def recalculate_delivery_performance(db:CurrentSessionTransaction)->ResponseSchemaModel[DeliveryRecalculateResult]:return response_base.success(data=await delivery_service.recalculate(db))
@router.get('/orders',dependencies=view)
async def list_orders(db:CurrentSession,status:Annotated[str|None,Query()]=None)->ResponseSchemaModel[list[SalesOrderDetail]]:return response_base.success(data=await sales_service.list_orders(db,status))
@router.post('/orders',dependencies=[Depends(RequestPermission('erp:sales:create')),DependsRBAC])
async def create_order(db:CurrentSessionTransaction,obj:CreateSalesOrder)->ResponseSchemaModel[SalesOrderDetail]:return response_base.success(data=await sales_service.create_order(db,obj))
@router.get('/orders/{order_id}',dependencies=view)
async def get_order(db:CurrentSession,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[SalesOrderDetail]:return response_base.success(data=await sales_service.get_order(db,order_id))
@router.post('/orders/{order_id}/promise/assess',dependencies=[Depends(RequestPermission('erp:sales:confirm')),DependsRBAC])
async def assess_order_promise(db:CurrentSessionTransaction,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[list[PromiseAssessmentDetail]]:return response_base.success(data=await promise_service.assess_order(db,order_id))
@router.get('/orders/{order_id}/promise',dependencies=view)
async def list_order_promise(db:CurrentSession,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[list[PromiseAssessmentDetail]]:return response_base.success(data=await promise_service.list_assessments(db,order_id))
@router.get('/orders/{order_id}/delivery-performance',dependencies=view)
async def list_order_delivery_performance(db:CurrentSession,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[list[DeliveryPerformanceDetail]]:return response_base.success(data=await delivery_service.list_order_performance(db,order_id))
@router.post('/orders/{order_id}/confirm',dependencies=[Depends(RequestPermission('erp:sales:confirm')),DependsRBAC])
async def confirm_order(db:CurrentSessionTransaction,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[SalesOrderDetail]:return response_base.success(data=await sales_service.transition(db,order_id,'confirm'))
@router.post('/orders/{order_id}/cancel',dependencies=[Depends(RequestPermission('erp:sales:cancel')),DependsRBAC])
async def cancel_order(db:CurrentSessionTransaction,order_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[SalesOrderDetail]:return response_base.success(data=await sales_service.transition(db,order_id,'cancel'))
@router.get('/shipments',dependencies=view)
async def list_shipments(db:CurrentSession)->ResponseSchemaModel[list[ShipmentDetail]]:return response_base.success(data=await sales_service.list_shipments(db))
@router.post('/shipments',dependencies=[Depends(RequestPermission('erp:sales:shipment')),DependsRBAC])
async def create_shipment(db:CurrentSessionTransaction,obj:CreateShipment)->ResponseSchemaModel[ShipmentDetail]:return response_base.success(data=await sales_service.create_shipment(db,obj))
@router.post('/shipments/{shipment_id}/deliver',dependencies=[Depends(RequestPermission('erp:sales:shipment')),DependsRBAC])
async def deliver_shipment(db:CurrentSessionTransaction,shipment_id:Annotated[int,Path(ge=1)],obj:DeliverShipment)->ResponseSchemaModel[ShipmentDetail]:return response_base.success(data=await sales_service.deliver_shipment(db,shipment_id,obj.delivered_at))
