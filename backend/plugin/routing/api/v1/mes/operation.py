from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.routing.enums import OperationStatus, OperationType
from backend.plugin.routing.schema.routing import (
    CreateOperationParam,
    OperationDetail,
    OperationListItem,
    OperationOption,
    OperationStatusParam,
    UpdateOperationParam,
)
from backend.plugin.routing.service.routing_service import routing_service


router = APIRouter()


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_operation_options(
    db: CurrentSession, keyword: str | None = Query(default=None)
) -> ResponseSchemaModel[list[OperationOption]]:
    return response_base.success(data=await routing_service.list_operation_options(db, keyword))


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_operations(
    db: CurrentSession,
    keyword: str | None = Query(default=None),
    operation_type: OperationType | None = Query(default=None),
    status: OperationStatus | None = Query(default=None),
) -> ResponseSchemaModel[PageData[OperationListItem]]:
    return response_base.success(data=await routing_service.list_operations(db, keyword, operation_type, status))


@router.post('', dependencies=[Depends(RequestPermission('mes:operation:config')), DependsRBAC])
async def create_operation(
    db: CurrentSessionTransaction, obj: CreateOperationParam
) -> ResponseSchemaModel[OperationDetail]:
    item = await routing_service.create_operation(db, obj)
    return response_base.success(data=OperationDetail.model_validate(item))


@router.get('/{operation_id}', dependencies=[DependsJwtAuth])
async def get_operation(
    db: CurrentSession, operation_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[OperationDetail]:
    return response_base.success(data=await routing_service.get_operation(db, operation_id))


@router.put('/{operation_id}', dependencies=[Depends(RequestPermission('mes:operation:config')), DependsRBAC])
async def update_operation(
    db: CurrentSessionTransaction, operation_id: Annotated[int, Path(ge=1)], obj: UpdateOperationParam
) -> ResponseSchemaModel[OperationDetail]:
    item = await routing_service.update_operation(db, operation_id, obj)
    return response_base.success(data=OperationDetail.model_validate(item))


@router.put(
    '/{operation_id}/status', dependencies=[Depends(RequestPermission('mes:operation:status')), DependsRBAC]
)
async def update_operation_status(
    db: CurrentSessionTransaction, operation_id: Annotated[int, Path(ge=1)], obj: OperationStatusParam
) -> ResponseSchemaModel[OperationDetail]:
    item = await routing_service.update_operation_status(db, operation_id, obj.status)
    return response_base.success(data=OperationDetail.model_validate(item))
