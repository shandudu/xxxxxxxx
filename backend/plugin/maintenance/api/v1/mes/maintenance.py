from typing import Annotated

from decimal import Decimal
from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.maintenance.schema.maintenance import (
    AssignRepair,
    CloseDowntime,
    CompleteRepair,
    CompleteTask,
    CreateDowntime,
    CreateMaintenancePlan,
    CreateRepairOrder,
    DowntimeDetail,
    GenerateDueTasks,
    MaintenanceDashboard,
    MaintenancePlanDetail,
    MaintenanceTaskDetail,
    RepairOrderDetail,
    StartRepair,
    StartTask,
    UpdateMaintenancePlan,
    IssueRepairPart,
    RepairPartIssueDetail,
    PostRepairCost,
    RepairCostPostingDetail,
    RepairCostAnalysisSummary,
)
from backend.plugin.maintenance.service import maintenance_service


router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:maintenance:view')), DependsRBAC]


@router.get('/dashboard', dependencies=view_dependencies)
async def dashboard(db: CurrentSession) -> ResponseSchemaModel[MaintenanceDashboard]:
    return response_base.success(data=await maintenance_service.dashboard(db))


@router.get('/plans', dependencies=view_dependencies)
async def list_plans(db: CurrentSession) -> ResponseSchemaModel[list[MaintenancePlanDetail]]:
    return response_base.success(data=await maintenance_service.list_plans(db))


@router.post('/plans', dependencies=[Depends(RequestPermission('mes:maintenance:config')), DependsRBAC])
async def create_plan(db: CurrentSessionTransaction, obj: CreateMaintenancePlan) -> ResponseSchemaModel[MaintenancePlanDetail]:
    return response_base.success(data=await maintenance_service.create_plan(db, obj))


@router.put('/plans/{plan_id}', dependencies=[Depends(RequestPermission('mes:maintenance:config')), DependsRBAC])
async def update_plan(db: CurrentSessionTransaction, plan_id: Annotated[int, Path(ge=1)], obj: UpdateMaintenancePlan) -> ResponseSchemaModel[MaintenancePlanDetail]:
    return response_base.success(data=await maintenance_service.update_plan(db, plan_id, obj))


@router.post('/plans/generate-due', dependencies=[Depends(RequestPermission('mes:maintenance:generate')), DependsRBAC])
async def generate_due_tasks(db: CurrentSessionTransaction, obj: GenerateDueTasks) -> ResponseSchemaModel[list[MaintenanceTaskDetail]]:
    return response_base.success(data=await maintenance_service.generate_due_tasks(db, obj))


@router.get('/tasks', dependencies=view_dependencies)
async def list_tasks(db: CurrentSession) -> ResponseSchemaModel[list[MaintenanceTaskDetail]]:
    return response_base.success(data=await maintenance_service.list_tasks(db))


@router.post('/tasks/{task_id}/start', dependencies=[Depends(RequestPermission('mes:maintenance:execute')), DependsRBAC])
async def start_task(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)], obj: StartTask) -> ResponseSchemaModel[MaintenanceTaskDetail]:
    return response_base.success(data=await maintenance_service.start_task(db, task_id, obj))


@router.post('/tasks/{task_id}/complete', dependencies=[Depends(RequestPermission('mes:maintenance:execute')), DependsRBAC])
async def complete_task(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)], obj: CompleteTask) -> ResponseSchemaModel[MaintenanceTaskDetail]:
    return response_base.success(data=await maintenance_service.complete_task(db, task_id, obj))


@router.get('/repairs', dependencies=view_dependencies)
async def list_repairs(db: CurrentSession) -> ResponseSchemaModel[list[RepairOrderDetail]]:
    return response_base.success(data=await maintenance_service.list_repairs(db))


@router.post('/repairs', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def create_repair(db: CurrentSessionTransaction, obj: CreateRepairOrder) -> ResponseSchemaModel[RepairOrderDetail]:
    return response_base.success(data=await maintenance_service.create_repair(db, obj))


@router.post('/repairs/{repair_id}/assign', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def assign_repair(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)], obj: AssignRepair) -> ResponseSchemaModel[RepairOrderDetail]:
    return response_base.success(data=await maintenance_service.assign_repair(db, repair_id, obj))


@router.post('/repairs/{repair_id}/start', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def start_repair(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)], obj: StartRepair) -> ResponseSchemaModel[RepairOrderDetail]:
    return response_base.success(data=await maintenance_service.start_repair(db, repair_id, obj))


@router.post('/repairs/{repair_id}/complete', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def complete_repair(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)], obj: CompleteRepair) -> ResponseSchemaModel[RepairOrderDetail]:
    return response_base.success(data=await maintenance_service.complete_repair(db, repair_id, obj))


@router.get('/repairs/cost-analysis', dependencies=view_dependencies)
async def repair_cost_analysis(db: CurrentSession, period_id: int | None = Query(default=None, ge=1), hourly_downtime_cost: Decimal = Query(default=Decimal('0'), ge=0)) -> ResponseSchemaModel[RepairCostAnalysisSummary]:
    return response_base.success(data=await maintenance_service.repair_cost_analysis(db, period_id, hourly_downtime_cost))


@router.get('/repairs/{repair_id}/parts', dependencies=view_dependencies)
async def list_repair_parts(db: CurrentSession, repair_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[RepairPartIssueDetail]]:
    return response_base.success(data=await maintenance_service.list_repair_parts(db, repair_id))


@router.post('/repairs/{repair_id}/parts', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def issue_repair_part(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)], obj: IssueRepairPart) -> ResponseSchemaModel[RepairPartIssueDetail]:
    return response_base.success(data=await maintenance_service.issue_repair_part(db, repair_id, obj))


@router.post('/repairs/{repair_id}/cost/post', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def post_repair_cost(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)], obj: PostRepairCost) -> ResponseSchemaModel[RepairCostPostingDetail]:
    return response_base.success(data=await maintenance_service.post_repair_cost(db, repair_id, obj))


@router.post('/repairs/{repair_id}/cancel', dependencies=[Depends(RequestPermission('mes:maintenance:repair')), DependsRBAC])
async def cancel_repair(db: CurrentSessionTransaction, repair_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[RepairOrderDetail]:
    return response_base.success(data=await maintenance_service.cancel_repair(db, repair_id))


@router.get('/downtimes', dependencies=view_dependencies)
async def list_downtimes(db: CurrentSession) -> ResponseSchemaModel[list[DowntimeDetail]]:
    return response_base.success(data=await maintenance_service.list_downtimes(db))


@router.post('/downtimes', dependencies=[Depends(RequestPermission('mes:maintenance:downtime')), DependsRBAC])
async def create_downtime(db: CurrentSessionTransaction, obj: CreateDowntime) -> ResponseSchemaModel[DowntimeDetail]:
    return response_base.success(data=await maintenance_service.create_downtime(db, obj))


@router.post('/downtimes/{downtime_id}/close', dependencies=[Depends(RequestPermission('mes:maintenance:downtime')), DependsRBAC])
async def close_downtime(db: CurrentSessionTransaction, downtime_id: Annotated[int, Path(ge=1)], obj: CloseDowntime) -> ResponseSchemaModel[DowntimeDetail]:
    return response_base.success(data=await maintenance_service.close_downtime(db, downtime_id, obj))
