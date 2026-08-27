from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.costing.enums import MarginDimension
from backend.plugin.costing.schema.costing import CostCalculateRequest, CostPeriodCreate, CostPeriodDetail, MarginDashboard, WorkOrderCostDetail
from backend.plugin.costing.service import costing_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('erp:costing:view')), DependsRBAC]


@router.get('/periods', dependencies=view_dependencies)
async def periods(db: CurrentSession) -> ResponseSchemaModel[list[CostPeriodDetail]]:
    return response_base.success(data=await costing_service.periods(db))


@router.post('/periods', dependencies=[Depends(RequestPermission('erp:costing:manage')), DependsRBAC])
async def create_period(db: CurrentSessionTransaction, obj: CostPeriodCreate) -> ResponseSchemaModel[CostPeriodDetail]:
    return response_base.success(data=await costing_service.create_period(db, obj))


@router.post('/work-orders/{work_order_id}/calculate', dependencies=[Depends(RequestPermission('erp:costing:calculate')), DependsRBAC])
async def calculate_work_order(db: CurrentSessionTransaction, work_order_id: Annotated[int, Path(ge=1)], obj: CostCalculateRequest) -> ResponseSchemaModel[WorkOrderCostDetail]:
    return response_base.success(data=await costing_service.calculate_work_order(db, work_order_id, obj.period_id))


@router.get('/work-orders/{work_order_id}', dependencies=view_dependencies)
async def work_order_cost(db: CurrentSession, work_order_id: Annotated[int, Path(ge=1)], period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[WorkOrderCostDetail]:
    cost = await costing_service.work_order_cost(db, work_order_id, period_id)
    return response_base.success(data=cost)


@router.post('/work-orders/{work_order_id}/post', dependencies=[Depends(RequestPermission('erp:costing:post')), DependsRBAC])
async def post_work_order(db: CurrentSessionTransaction, work_order_id: Annotated[int, Path(ge=1)], obj: CostCalculateRequest) -> ResponseSchemaModel[WorkOrderCostDetail]:
    return response_base.success(data=await costing_service.post_work_order(db, work_order_id, obj.period_id))


@router.post('/periods/{period_id}/close', dependencies=[Depends(RequestPermission('erp:costing:close')), DependsRBAC])
async def close_period(db: CurrentSessionTransaction, period_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CostPeriodDetail]:
    return response_base.success(data=await costing_service.close_period(db, period_id))


@router.get('/margins', dependencies=view_dependencies)
async def margins(db: CurrentSession, dimension: MarginDimension = Query(default=MarginDimension.PRODUCT), period_id: int | None = Query(default=None, ge=1)) -> ResponseSchemaModel[MarginDashboard]:
    return response_base.success(data=await costing_service.margin(db, period_id, dimension))
