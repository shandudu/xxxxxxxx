from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.routing.enums import WorkCenterStatus, WorkCenterType
from backend.plugin.routing.schema.routing import (
    CreateWorkCenterParam,
    UpdateWorkCenterParam,
    WorkCenterDetail,
    WorkCenterOption,
    WorkCenterStatusParam,
)
from backend.plugin.routing.service.routing_service import routing_service


router = APIRouter()


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_work_center_options(
    db: CurrentSession, keyword: str | None = Query(default=None)
) -> ResponseSchemaModel[list[WorkCenterOption]]:
    return response_base.success(data=await routing_service.list_work_center_options(db, keyword))


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_work_centers(
    db: CurrentSession,
    keyword: str | None = Query(default=None),
    work_center_type: WorkCenterType | None = Query(default=None),
    status: WorkCenterStatus | None = Query(default=None),
) -> ResponseSchemaModel[PageData[WorkCenterDetail]]:
    return response_base.success(data=await routing_service.list_work_centers(db, keyword, work_center_type, status))


@router.post('', dependencies=[Depends(RequestPermission('mes:workcenter:config')), DependsRBAC])
async def create_work_center(
    db: CurrentSessionTransaction, obj: CreateWorkCenterParam
) -> ResponseSchemaModel[WorkCenterDetail]:
    item = await routing_service.create_work_center(db, obj)
    return response_base.success(data=WorkCenterDetail.model_validate(item))


@router.get('/{work_center_id}', dependencies=[DependsJwtAuth])
async def get_work_center(
    db: CurrentSession, work_center_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[WorkCenterDetail]:
    return response_base.success(data=await routing_service.get_work_center(db, work_center_id))


@router.put(
    '/{work_center_id}', dependencies=[Depends(RequestPermission('mes:workcenter:config')), DependsRBAC]
)
async def update_work_center(
    db: CurrentSessionTransaction, work_center_id: Annotated[int, Path(ge=1)], obj: UpdateWorkCenterParam
) -> ResponseSchemaModel[WorkCenterDetail]:
    item = await routing_service.update_work_center(db, work_center_id, obj)
    return response_base.success(data=WorkCenterDetail.model_validate(item))


@router.put(
    '/{work_center_id}/status', dependencies=[Depends(RequestPermission('mes:workcenter:status')), DependsRBAC]
)
async def update_work_center_status(
    db: CurrentSessionTransaction, work_center_id: Annotated[int, Path(ge=1)], obj: WorkCenterStatusParam
) -> ResponseSchemaModel[WorkCenterDetail]:
    item = await routing_service.update_work_center_status(db, work_center_id, obj.status)
    return response_base.success(data=WorkCenterDetail.model_validate(item))
