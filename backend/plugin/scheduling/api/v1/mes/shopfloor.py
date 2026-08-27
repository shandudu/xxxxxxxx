from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.scheduling.schema.shopfloor import (
    CheckInInput,
    CompleteDispatchInput,
    StatusInput,
    TeamDetail,
    TeamInput,
    TeamMemberInput,
    TerminalContext,
    TerminalDispatchDetail,
    UserOption,
    WorkstationDetail,
    WorkstationInput,
    WorkstationOption,
    WorkstationSessionDetail,
)
from backend.plugin.scheduling.service import shopfloor_service


router = APIRouter()
view = [DependsJwtAuth, Depends(RequestPermission('mes:shopfloor:view')), DependsRBAC]


@router.get('/teams', dependencies=view)
async def teams(db: CurrentSession) -> ResponseSchemaModel[list[TeamDetail]]:
    return response_base.success(data=await shopfloor_service.list_teams(db))


@router.post('/teams', dependencies=[Depends(RequestPermission('mes:shopfloor:team')), DependsRBAC])
async def create_team(db: CurrentSessionTransaction, obj: TeamInput) -> ResponseSchemaModel[TeamDetail]:
    return response_base.success(data=await shopfloor_service.create_team(db, obj))


@router.put('/teams/{team_id}', dependencies=[Depends(RequestPermission('mes:shopfloor:team')), DependsRBAC])
async def update_team(db: CurrentSessionTransaction, team_id: Annotated[int, Path(ge=1)], obj: TeamInput) -> ResponseSchemaModel[TeamDetail]:
    return response_base.success(data=await shopfloor_service.update_team(db, team_id, obj))


@router.put('/teams/{team_id}/status', dependencies=[Depends(RequestPermission('mes:shopfloor:team')), DependsRBAC])
async def team_status(db: CurrentSessionTransaction, team_id: Annotated[int, Path(ge=1)], obj: StatusInput) -> ResponseSchemaModel[TeamDetail]:
    return response_base.success(data=await shopfloor_service.team_status(db, team_id, obj))


@router.post('/teams/{team_id}/members', dependencies=[Depends(RequestPermission('mes:shopfloor:team')), DependsRBAC])
async def add_member(db: CurrentSessionTransaction, team_id: Annotated[int, Path(ge=1)], obj: TeamMemberInput) -> ResponseSchemaModel[TeamDetail]:
    return response_base.success(data=await shopfloor_service.add_member(db, team_id, obj))


@router.put('/teams/{team_id}/members/{member_id}/status', dependencies=[Depends(RequestPermission('mes:shopfloor:team')), DependsRBAC])
async def member_status(db: CurrentSessionTransaction, team_id: Annotated[int, Path(ge=1)], member_id: Annotated[int, Path(ge=1)], obj: StatusInput) -> ResponseSchemaModel[TeamDetail]:
    return response_base.success(data=await shopfloor_service.member_status(db, team_id, member_id, obj))


@router.get('/users/options', dependencies=view)
async def user_options(db: CurrentSession) -> ResponseSchemaModel[list[UserOption]]:
    return response_base.success(data=await shopfloor_service.users(db))


@router.get('/workstations', dependencies=view)
async def workstations(db: CurrentSession) -> ResponseSchemaModel[list[WorkstationDetail]]:
    return response_base.success(data=await shopfloor_service.list_workstations(db))


@router.post('/workstations', dependencies=[Depends(RequestPermission('mes:shopfloor:workstation')), DependsRBAC])
async def create_workstation(db: CurrentSessionTransaction, obj: WorkstationInput) -> ResponseSchemaModel[WorkstationDetail]:
    return response_base.success(data=await shopfloor_service.create_workstation(db, obj))


@router.put('/workstations/{workstation_id}', dependencies=[Depends(RequestPermission('mes:shopfloor:workstation')), DependsRBAC])
async def update_workstation(db: CurrentSessionTransaction, workstation_id: Annotated[int, Path(ge=1)], obj: WorkstationInput) -> ResponseSchemaModel[WorkstationDetail]:
    return response_base.success(data=await shopfloor_service.update_workstation(db, workstation_id, obj))


@router.put('/workstations/{workstation_id}/status', dependencies=[Depends(RequestPermission('mes:shopfloor:workstation')), DependsRBAC])
async def workstation_status(db: CurrentSessionTransaction, workstation_id: Annotated[int, Path(ge=1)], obj: StatusInput) -> ResponseSchemaModel[WorkstationDetail]:
    return response_base.success(data=await shopfloor_service.workstation_status(db, workstation_id, obj))


@router.get('/workstations/options', dependencies=view)
async def workstation_options(db: CurrentSession) -> ResponseSchemaModel[list[WorkstationOption]]:
    return response_base.success(data=await shopfloor_service.workstation_options(db))


@router.get('/terminal/{workstation_id}/context', dependencies=view)
async def terminal_context(db: CurrentSession, workstation_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[TerminalContext]:
    return response_base.success(data=await shopfloor_service.terminal_context(db, workstation_id))


@router.post('/terminal/{workstation_id}/check-in', dependencies=[Depends(RequestPermission('mes:shopfloor:operate')), DependsRBAC])
async def check_in(db: CurrentSessionTransaction, workstation_id: Annotated[int, Path(ge=1)], obj: CheckInInput) -> ResponseSchemaModel[WorkstationSessionDetail]:
    return response_base.success(data=await shopfloor_service.check_in(db, workstation_id, obj))


@router.post('/terminal/sessions/{session_id}/check-out', dependencies=[Depends(RequestPermission('mes:shopfloor:operate')), DependsRBAC])
async def check_out(db: CurrentSessionTransaction, session_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkstationSessionDetail]:
    return response_base.success(data=await shopfloor_service.check_out(db, session_id))


@router.post('/terminal/{workstation_id}/dispatches/{dispatch_id}/start', dependencies=[Depends(RequestPermission('mes:shopfloor:operate')), DependsRBAC])
async def start_dispatch(db: CurrentSessionTransaction, workstation_id: Annotated[int, Path(ge=1)], dispatch_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[TerminalDispatchDetail]:
    return response_base.success(data=await shopfloor_service.start_dispatch(db, dispatch_id, workstation_id))


@router.post('/terminal/{workstation_id}/dispatches/{dispatch_id}/complete', dependencies=[Depends(RequestPermission('mes:shopfloor:operate')), DependsRBAC])
async def complete_dispatch(db: CurrentSessionTransaction, workstation_id: Annotated[int, Path(ge=1)], dispatch_id: Annotated[int, Path(ge=1)], obj: CompleteDispatchInput) -> ResponseSchemaModel[TerminalDispatchDetail]:
    return response_base.success(data=await shopfloor_service.complete_dispatch(db, dispatch_id, workstation_id, obj))
