from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.planning.schema.planning import (
    CreateMpsDemand,
    CreateMpsPlan,
    CreateMrpRun,
    ImportSalesOrderDemand,
    MpsDemandDetail,
    MpsPlanDetail,
    MrpRunDetail,
    PlannedOrderDetail,
    ReleasePlannedOrder,
)
from backend.plugin.planning.service import planning_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:planning:view')), DependsRBAC]


@router.get('/mps-plans', dependencies=view_dependencies)
async def list_mps_plans(
    db: CurrentSession,
    status: Annotated[str | None, Query(max_length=20)] = None,
) -> ResponseSchemaModel[list[MpsPlanDetail]]:
    return response_base.success(data=await planning_service.list_plans(db, status))


@router.post(
    '/mps-plans',
    dependencies=[Depends(RequestPermission('mes:planning:create')), DependsRBAC],
)
async def create_mps_plan(
    db: CurrentSessionTransaction,
    obj: CreateMpsPlan,
) -> ResponseSchemaModel[MpsPlanDetail]:
    return response_base.success(data=await planning_service.create_plan(db, obj))


@router.get('/mps-plans/{plan_id}', dependencies=view_dependencies)
async def get_mps_plan(
    db: CurrentSession,
    plan_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[MpsPlanDetail]:
    return response_base.success(data=await planning_service.get_plan(db, plan_id))


@router.post(
    '/mps-plans/{plan_id}/demands',
    dependencies=[Depends(RequestPermission('mes:planning:create')), DependsRBAC],
)
async def add_mps_demand(
    db: CurrentSessionTransaction,
    plan_id: Annotated[int, Path(ge=1)],
    obj: CreateMpsDemand,
) -> ResponseSchemaModel[MpsDemandDetail]:
    return response_base.success(data=await planning_service.add_demand(db, plan_id, obj))


@router.post(
    '/mps-plans/{plan_id}/import-sales-orders',
    dependencies=[Depends(RequestPermission('mes:planning:create')), DependsRBAC],
)
async def import_sales_order_demands(
    db: CurrentSessionTransaction,
    plan_id: Annotated[int, Path(ge=1)],
    obj: ImportSalesOrderDemand,
) -> ResponseSchemaModel[list[MpsDemandDetail]]:
    return response_base.success(data=await planning_service.import_sales_orders(db, plan_id, obj))


@router.delete(
    '/mps-plans/{plan_id}/demands/{demand_id}',
    dependencies=[Depends(RequestPermission('mes:planning:create')), DependsRBAC],
)
async def delete_mps_demand(
    db: CurrentSessionTransaction,
    plan_id: Annotated[int, Path(ge=1)],
    demand_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[None]:
    await planning_service.delete_demand(db, plan_id, demand_id)
    return response_base.success()


@router.post(
    '/mps-plans/{plan_id}/confirm',
    dependencies=[Depends(RequestPermission('mes:planning:confirm')), DependsRBAC],
)
async def confirm_mps_plan(
    db: CurrentSessionTransaction,
    plan_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[MpsPlanDetail]:
    return response_base.success(data=await planning_service.confirm_plan(db, plan_id))


@router.get('/mrp-runs', dependencies=view_dependencies)
async def list_mrp_runs(
    db: CurrentSession,
    plan_id: Annotated[int | None, Query(ge=1)] = None,
) -> ResponseSchemaModel[list[MrpRunDetail]]:
    return response_base.success(data=await planning_service.list_runs(db, plan_id))


@router.post(
    '/mrp-runs',
    dependencies=[Depends(RequestPermission('mes:planning:run')), DependsRBAC],
)
async def run_mrp(
    db: CurrentSessionTransaction,
    obj: CreateMrpRun,
) -> ResponseSchemaModel[MrpRunDetail]:
    return response_base.success(data=await planning_service.run_mrp(db, obj))


@router.get('/mrp-runs/{run_id}', dependencies=view_dependencies)
async def get_mrp_run(
    db: CurrentSession,
    run_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[MrpRunDetail]:
    return response_base.success(data=await planning_service.get_run(db, run_id))


@router.post(
    '/planned-orders/{planned_order_id}/firm',
    dependencies=[Depends(RequestPermission('mes:planning:firm')), DependsRBAC],
)
async def firm_planned_order(
    db: CurrentSessionTransaction,
    planned_order_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[PlannedOrderDetail]:
    return response_base.success(data=await planning_service.firm_planned_order(db, planned_order_id))


@router.post(
    '/planned-orders/{planned_order_id}/release',
    dependencies=[Depends(RequestPermission('mes:planning:release')), DependsRBAC],
)
async def release_planned_order(
    db: CurrentSessionTransaction,
    planned_order_id: Annotated[int, Path(ge=1)],
    obj: ReleasePlannedOrder,
) -> ResponseSchemaModel[PlannedOrderDetail]:
    return response_base.success(
        data=await planning_service.release_planned_order(db, planned_order_id, obj)
    )
