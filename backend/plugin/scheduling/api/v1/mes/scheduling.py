from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.scheduling.schema.scheduling import (
    ApsScheduleDetail,
    ApsScheduleListItem,
    AssignWorkCenterCalendar,
    CalendarDetail,
    CreateApsSchedule,
    CreateCalendar,
    CreateDispatch,
    CreateShift,
    DispatchDetail,
    ShiftDetail,
    UpdateCalendar,
    UpdateShift,
    UpsertCalendarDay,
    WorkCenterLoad,
    WorkOrderCandidate,
)
from backend.plugin.scheduling.service import scheduling_service


router = APIRouter()
view_dependencies = [
    DependsJwtAuth,
    Depends(RequestPermission('mes:scheduling:view')),
    DependsRBAC,
]


@router.get('/shifts', dependencies=view_dependencies)
async def list_shifts(db: CurrentSession) -> ResponseSchemaModel[list[ShiftDetail]]:
    return response_base.success(data=await scheduling_service.list_shifts(db))


@router.post(
    '/shifts',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def create_shift(
    db: CurrentSessionTransaction, obj: CreateShift
) -> ResponseSchemaModel[ShiftDetail]:
    return response_base.success(data=await scheduling_service.create_shift(db, obj))


@router.put(
    '/shifts/{shift_id}',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def update_shift(
    db: CurrentSessionTransaction,
    shift_id: Annotated[int, Path(ge=1)],
    obj: UpdateShift,
) -> ResponseSchemaModel[ShiftDetail]:
    return response_base.success(data=await scheduling_service.update_shift(db, shift_id, obj))


@router.get('/calendars', dependencies=view_dependencies)
async def list_calendars(db: CurrentSession) -> ResponseSchemaModel[list[CalendarDetail]]:
    return response_base.success(data=await scheduling_service.list_calendars(db))


@router.post(
    '/calendars',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def create_calendar(
    db: CurrentSessionTransaction, obj: CreateCalendar
) -> ResponseSchemaModel[CalendarDetail]:
    return response_base.success(data=await scheduling_service.create_calendar(db, obj))


@router.get('/calendars/{calendar_id}', dependencies=view_dependencies)
async def get_calendar(
    db: CurrentSession, calendar_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[CalendarDetail]:
    return response_base.success(data=await scheduling_service.calendar_detail(db, calendar_id))


@router.put(
    '/calendars/{calendar_id}',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def update_calendar(
    db: CurrentSessionTransaction,
    calendar_id: Annotated[int, Path(ge=1)],
    obj: UpdateCalendar,
) -> ResponseSchemaModel[CalendarDetail]:
    return response_base.success(
        data=await scheduling_service.update_calendar(db, calendar_id, obj)
    )


@router.put(
    '/calendars/{calendar_id}/days',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def upsert_calendar_day(
    db: CurrentSessionTransaction,
    calendar_id: Annotated[int, Path(ge=1)],
    obj: UpsertCalendarDay,
) -> ResponseSchemaModel[CalendarDetail]:
    return response_base.success(
        data=await scheduling_service.upsert_calendar_day(db, calendar_id, obj)
    )


@router.post(
    '/calendars/{calendar_id}/work-centers',
    dependencies=[Depends(RequestPermission('mes:scheduling:config')), DependsRBAC],
)
async def assign_work_center(
    db: CurrentSessionTransaction,
    calendar_id: Annotated[int, Path(ge=1)],
    obj: AssignWorkCenterCalendar,
) -> ResponseSchemaModel[CalendarDetail]:
    return response_base.success(
        data=await scheduling_service.assign_work_center(db, calendar_id, obj)
    )


@router.get('/work-orders/options', dependencies=view_dependencies)
async def work_order_candidates(
    db: CurrentSession,
) -> ResponseSchemaModel[list[WorkOrderCandidate]]:
    return response_base.success(data=await scheduling_service.work_order_candidates(db))


@router.get('/schedules', dependencies=view_dependencies)
async def list_schedules(db: CurrentSession) -> ResponseSchemaModel[list[ApsScheduleListItem]]:
    return response_base.success(data=await scheduling_service.list_schedules(db))


@router.post(
    '/schedules',
    dependencies=[Depends(RequestPermission('mes:scheduling:run')), DependsRBAC],
)
async def run_schedule(
    db: CurrentSessionTransaction, obj: CreateApsSchedule
) -> ResponseSchemaModel[ApsScheduleDetail]:
    return response_base.success(data=await scheduling_service.run_schedule(db, obj))


@router.get('/schedules/{schedule_id}', dependencies=view_dependencies)
async def get_schedule(
    db: CurrentSession, schedule_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[ApsScheduleDetail]:
    return response_base.success(data=await scheduling_service.schedule_detail(db, schedule_id))


@router.post(
    '/schedules/{schedule_id}/publish',
    dependencies=[Depends(RequestPermission('mes:scheduling:publish')), DependsRBAC],
)
async def publish_schedule(
    db: CurrentSessionTransaction, schedule_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[ApsScheduleDetail]:
    return response_base.success(data=await scheduling_service.publish_schedule(db, schedule_id))


@router.get('/schedules/{schedule_id}/loads', dependencies=view_dependencies)
async def schedule_loads(
    db: CurrentSession, schedule_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[WorkCenterLoad]]:
    return response_base.success(data=await scheduling_service.work_center_loads(db, schedule_id))


@router.get('/dispatches', dependencies=view_dependencies)
async def list_dispatches(db: CurrentSession) -> ResponseSchemaModel[list[DispatchDetail]]:
    return response_base.success(data=await scheduling_service.list_dispatches(db))


@router.post(
    '/dispatches',
    dependencies=[Depends(RequestPermission('mes:scheduling:dispatch')), DependsRBAC],
)
async def create_dispatch(
    db: CurrentSessionTransaction, obj: CreateDispatch
) -> ResponseSchemaModel[DispatchDetail]:
    return response_base.success(data=await scheduling_service.create_dispatch(db, obj))


@router.post(
    '/dispatches/{dispatch_id}/accept',
    dependencies=[Depends(RequestPermission('mes:scheduling:dispatch')), DependsRBAC],
)
async def accept_dispatch(
    db: CurrentSessionTransaction, dispatch_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[DispatchDetail]:
    return response_base.success(data=await scheduling_service.accept_dispatch(db, dispatch_id))


@router.post(
    '/dispatches/{dispatch_id}/cancel',
    dependencies=[Depends(RequestPermission('mes:scheduling:dispatch')), DependsRBAC],
)
async def cancel_dispatch(
    db: CurrentSessionTransaction, dispatch_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[DispatchDetail]:
    return response_base.success(data=await scheduling_service.cancel_dispatch(db, dispatch_id))
