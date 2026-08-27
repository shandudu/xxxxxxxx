from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.production.model import MaterialConsumption, MaterialIssue, MaterialReturn, ProductionReport
from backend.plugin.production.schema.execution import (
    CompleteProductionExecution,
    MaterialConsumptionDetail,
    ProductionExecutionDetail,
    RecordMaterialConsumption,
    StartProductionExecution,
)
from backend.plugin.production.schema.production import AndonActionDetail, AndonAssignmentDetail, AndonDashboard, AndonEventDetail, AssignAndonEvent, CreateAndonEvent, CreateMaterialIssue, CreateMaterialReturn, CreateProductionReport, CreateWorkOrder, MaterialIssueDetail, MaterialVarianceDetail, ProductionDashboard, ResolveAndonEvent, WorkOrderDetail
from backend.plugin.production.service import andon_service, production_execution_service, production_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:production:view')), DependsRBAC]


@router.get('/andon/dashboard', dependencies=view_dependencies)
async def get_andon_dashboard(db: CurrentSession) -> ResponseSchemaModel[AndonDashboard]:
    return response_base.success(data=await andon_service.dashboard(db))


@router.get('/andon/events', dependencies=view_dependencies)
async def list_andon_events(db: CurrentSession, status: Annotated[str | None, Query(max_length=30)] = None, event_type: Annotated[str | None, Query(max_length=30)] = None) -> ResponseSchemaModel[list[AndonEventDetail]]:
    return response_base.success(data=await andon_service.list_events(db, status, event_type))


@router.post('/andon/events', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def create_andon_event(db: CurrentSessionTransaction, obj: CreateAndonEvent) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.create(db, obj))


@router.get('/andon/events/{event_id}', dependencies=view_dependencies)
async def get_andon_event(db: CurrentSession, event_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.get(db, event_id))


@router.post('/andon/events/{event_id}/assign', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def assign_andon_event(db: CurrentSessionTransaction, event_id: Annotated[int, Path(ge=1)], obj: AssignAndonEvent) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.assign(db, event_id, obj))


@router.post('/andon/events/{event_id}/start', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def start_andon_event(db: CurrentSessionTransaction, event_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.start(db, event_id))


@router.post('/andon/events/{event_id}/resolve', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def resolve_andon_event(db: CurrentSessionTransaction, event_id: Annotated[int, Path(ge=1)], obj: ResolveAndonEvent) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.resolve(db, event_id, obj))


@router.post('/andon/events/{event_id}/escalate', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def escalate_andon_event(db: CurrentSessionTransaction, event_id: Annotated[int, Path(ge=1)], notes: Annotated[str | None, Query(max_length=2000)] = None) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.escalate(db, event_id, notes))


@router.post('/andon/events/{event_id}/cancel', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def cancel_andon_event(db: CurrentSessionTransaction, event_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AndonEventDetail]:
    return response_base.success(data=await andon_service.cancel(db, event_id))


@router.get('/andon/events/{event_id}/assignments', dependencies=view_dependencies)
async def list_andon_assignments(db: CurrentSession, event_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[AndonAssignmentDetail]]:
    return response_base.success(data=[AndonAssignmentDetail.model_validate(item) for item in await andon_service.list_assignments(db, event_id)])


@router.get('/andon/events/{event_id}/actions', dependencies=view_dependencies)
async def list_andon_actions(db: CurrentSession, event_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[AndonActionDetail]]:
    return response_base.success(data=[AndonActionDetail.model_validate(item) for item in await andon_service.list_actions(db, event_id)])


@router.get('/dashboard', dependencies=view_dependencies)
async def get_dashboard(db: CurrentSession) -> ResponseSchemaModel[ProductionDashboard]:
    return response_base.success(data=await production_service.dashboard(db))


@router.get('/work-orders', dependencies=view_dependencies)
async def list_orders(db: CurrentSession, status: Annotated[str | None, Query(max_length=30)] = None) -> ResponseSchemaModel[list[WorkOrderDetail]]:
    return response_base.success(data=await production_service.list_orders(db, status))


@router.post('/work-orders', dependencies=[Depends(RequestPermission('mes:production:create')), DependsRBAC])
async def create_order(db: CurrentSessionTransaction, obj: CreateWorkOrder) -> ResponseSchemaModel[WorkOrderDetail]:
    return response_base.success(data=await production_service.create_order(db, obj))


@router.get('/work-orders/{order_id}', dependencies=view_dependencies)
async def get_order(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkOrderDetail]:
    return response_base.success(data=await production_service.get_order(db, order_id))


@router.get('/work-orders/{order_id}/material-variance', dependencies=view_dependencies)
async def get_material_variance(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[MaterialVarianceDetail]]:
    return response_base.success(data=await production_service.material_variance(db, order_id))


@router.post('/work-orders/{order_id}/release', dependencies=[Depends(RequestPermission('mes:production:release')), DependsRBAC])
async def release_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkOrderDetail]:
    return response_base.success(data=await production_service.release_order(db, order_id))


@router.post('/work-orders/{order_id}/start', dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC])
async def start_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkOrderDetail]:
    return response_base.success(data=await production_service.start_order(db, order_id))


@router.post('/material-issues', dependencies=[Depends(RequestPermission('mes:production:issue')), DependsRBAC])
async def issue_material(db: CurrentSessionTransaction, obj: CreateMaterialIssue) -> ResponseSchemaModel[MaterialIssueDetail]:
    return response_base.success(data=await production_service.issue_material(db, obj))


@router.get('/work-orders/{order_id}/material-issues', dependencies=view_dependencies)
async def list_material_issues(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[MaterialIssueDetail]]:
    return response_base.success(data=await production_service.list_issues(db, order_id))


@router.post('/material-returns', dependencies=[Depends(RequestPermission('mes:production:return')), DependsRBAC])
async def return_material(db: CurrentSessionTransaction, obj: CreateMaterialReturn) -> ResponseSchemaModel[MaterialReturn]:
    return response_base.success(data=await production_service.return_material(db, obj))


@router.post('/reports', dependencies=[Depends(RequestPermission('mes:production:report')), DependsRBAC])
async def report_completion(db: CurrentSessionTransaction, obj: CreateProductionReport) -> ResponseSchemaModel[ProductionReport]:
    return response_base.success(data=await production_service.report_completion(db, obj))


@router.get('/work-orders/{order_id}/executions', dependencies=view_dependencies)
async def list_executions(
    db: CurrentSession,
    order_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[list[ProductionExecutionDetail]]:
    return response_base.success(data=await production_execution_service.list_for_order(db, order_id))


@router.post(
    '/work-orders/{order_id}/operations/{operation_id}/executions/start',
    dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC],
)
async def start_execution(
    db: CurrentSessionTransaction,
    order_id: Annotated[int, Path(ge=1)],
    operation_id: Annotated[int, Path(ge=1)],
    obj: StartProductionExecution,
) -> ResponseSchemaModel[ProductionExecutionDetail]:
    return response_base.success(data=await production_execution_service.start(db, order_id, operation_id, obj))


@router.get('/executions/{execution_id}', dependencies=view_dependencies)
async def get_execution(
    db: CurrentSession,
    execution_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[ProductionExecutionDetail]:
    return response_base.success(data=await production_execution_service.get(db, execution_id))


@router.get('/executions/{execution_id}/consumptions', dependencies=view_dependencies)
async def list_consumptions(
    db: CurrentSession,
    execution_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[list[MaterialConsumptionDetail]]:
    await production_execution_service._execution(db, execution_id)
    return response_base.success(data=await production_execution_service.consumptions(db, execution_id))


@router.post(
    '/executions/{execution_id}/consumptions',
    dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC],
)
async def record_consumption(
    db: CurrentSessionTransaction,
    execution_id: Annotated[int, Path(ge=1)],
    obj: RecordMaterialConsumption,
) -> ResponseSchemaModel[MaterialConsumption]:
    return response_base.success(data=await production_execution_service.consume(db, execution_id, obj))


@router.post(
    '/executions/{execution_id}/complete',
    dependencies=[Depends(RequestPermission('mes:production:execute')), DependsRBAC],
)
async def complete_execution(
    db: CurrentSessionTransaction,
    execution_id: Annotated[int, Path(ge=1)],
    obj: CompleteProductionExecution,
) -> ResponseSchemaModel[ProductionExecutionDetail]:
    return response_base.success(data=await production_execution_service.complete(db, execution_id, obj))
