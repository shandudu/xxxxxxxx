from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.routing.enums import RoutingStatus, RoutingType
from backend.plugin.routing.schema.routing import (
    ActivateRoutingParam,
    CalculateRoutingTimeParam,
    CopyRoutingParam,
    CreateRoutingOperationParam,
    CreateRoutingParam,
    ReorderRoutingOperationParam,
    RoutingDetail,
    RoutingListItem,
    RoutingOperationDetail,
    RoutingOption,
    RoutingTimeCalculation,
    RoutingValidationResult,
    UpdateRoutingOperationParam,
    UpdateRoutingParam,
)
from backend.plugin.routing.service.routing_service import routing_service


router = APIRouter()


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_routing_options(
    db: CurrentSession,
    product_material_id: Annotated[int, Query(ge=1)],
    routing_type: RoutingType = Query(default=RoutingType.STANDARD),
    production_date: datetime | None = Query(default=None),
) -> ResponseSchemaModel[list[RoutingOption]]:
    return response_base.success(
        data=await routing_service.list_routing_options(db, product_material_id, routing_type, production_date)
    )


@router.get('/default', dependencies=[DependsJwtAuth])
async def get_default_routing(
    db: CurrentSession,
    product_material_id: Annotated[int, Query(ge=1)],
    routing_type: RoutingType = Query(default=RoutingType.STANDARD),
    production_date: datetime | None = Query(default=None),
) -> ResponseSchemaModel[RoutingOption | None]:
    return response_base.success(
        data=await routing_service.get_default_routing(db, product_material_id, routing_type, production_date)
    )


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_routings(
    db: CurrentSession,
    keyword: str | None = Query(default=None),
    product_material_id: int | None = Query(default=None, ge=1),
    status: RoutingStatus | None = Query(default=None),
    routing_type: RoutingType | None = Query(default=None),
    is_default: bool | None = Query(default=None),
    effective_date: datetime | None = Query(default=None),
) -> ResponseSchemaModel[PageData[RoutingListItem]]:
    return response_base.success(
        data=await routing_service.list_routings(
            db, keyword, product_material_id, status, routing_type, is_default, effective_date
        )
    )


@router.post('', dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC])
async def create_routing(
    db: CurrentSessionTransaction, obj: CreateRoutingParam
) -> ResponseSchemaModel[RoutingDetail]:
    item = await routing_service.create_routing(db, obj)
    return response_base.success(data=await routing_service.get_routing(db, item.id))


@router.get('/{routing_id}', dependencies=[DependsJwtAuth])
async def get_routing(
    db: CurrentSession, routing_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[RoutingDetail]:
    return response_base.success(data=await routing_service.get_routing(db, routing_id))


@router.put('/{routing_id}', dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC])
async def update_routing(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)], obj: UpdateRoutingParam
) -> ResponseSchemaModel[RoutingDetail]:
    await routing_service.update_routing(db, routing_id, obj)
    return response_base.success(data=await routing_service.get_routing(db, routing_id))


@router.post('/{routing_id}/copy', dependencies=[Depends(RequestPermission('mes:routing:copy')), DependsRBAC])
async def copy_routing(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)], obj: CopyRoutingParam
) -> ResponseSchemaModel[RoutingDetail]:
    return response_base.success(data=await routing_service.copy_routing(db, routing_id, obj))


@router.post('/{routing_id}/validate', dependencies=[Depends(RequestPermission('mes:routing:validate')), DependsRBAC])
async def validate_routing(
    db: CurrentSession, routing_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[RoutingValidationResult]:
    return response_base.success(data=await routing_service.validate_routing(db, routing_id))


@router.post('/{routing_id}/activate', dependencies=[Depends(RequestPermission('mes:routing:activate')), DependsRBAC])
async def activate_routing(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)], obj: ActivateRoutingParam
) -> ResponseSchemaModel[RoutingDetail]:
    await routing_service.activate_routing(db, routing_id, obj)
    return response_base.success(data=await routing_service.get_routing(db, routing_id))


@router.post('/{routing_id}/deactivate', dependencies=[Depends(RequestPermission('mes:routing:deactivate')), DependsRBAC])
async def deactivate_routing(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[RoutingDetail]:
    await routing_service.deactivate_routing(db, routing_id)
    return response_base.success(data=await routing_service.get_routing(db, routing_id))


@router.put('/{routing_id}/default', dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC])
async def set_default_routing(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[RoutingDetail]:
    await routing_service.set_default_routing(db, routing_id)
    return response_base.success(data=await routing_service.get_routing(db, routing_id))


@router.post('/{routing_id}/calculate-time', dependencies=[DependsJwtAuth])
async def calculate_routing_time(
    db: CurrentSession, routing_id: Annotated[int, Path(ge=1)], obj: CalculateRoutingTimeParam
) -> ResponseSchemaModel[RoutingTimeCalculation]:
    return response_base.success(data=await routing_service.calculate_time(db, routing_id, obj))


@router.get('/{routing_id}/operations', dependencies=[DependsJwtAuth])
async def list_routing_operations(
    db: CurrentSession, routing_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[RoutingOperationDetail]]:
    return response_base.success(data=await routing_service.list_routing_operations(db, routing_id))


@router.post('/{routing_id}/operations', dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC])
async def add_routing_operation(
    db: CurrentSessionTransaction, routing_id: Annotated[int, Path(ge=1)], obj: CreateRoutingOperationParam
) -> ResponseSchemaModel[RoutingOperationDetail]:
    return response_base.success(data=await routing_service.add_routing_operation(db, routing_id, obj))


@router.put(
    '/{routing_id}/operations/reorder', dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC]
)
async def reorder_routing_operations(
    db: CurrentSessionTransaction,
    routing_id: Annotated[int, Path(ge=1)],
    obj: ReorderRoutingOperationParam,
) -> ResponseSchemaModel[list[RoutingOperationDetail]]:
    return response_base.success(data=await routing_service.reorder_routing_operations(db, routing_id, obj))


@router.put(
    '/{routing_id}/operations/{routing_operation_id}',
    dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC],
)
async def update_routing_operation(
    db: CurrentSessionTransaction,
    routing_id: Annotated[int, Path(ge=1)],
    routing_operation_id: Annotated[int, Path(ge=1)],
    obj: UpdateRoutingOperationParam,
) -> ResponseSchemaModel[RoutingOperationDetail]:
    return response_base.success(
        data=await routing_service.update_routing_operation(db, routing_id, routing_operation_id, obj)
    )


@router.delete(
    '/{routing_id}/operations/{routing_operation_id}',
    dependencies=[Depends(RequestPermission('mes:routing:config')), DependsRBAC],
)
async def delete_routing_operation(
    db: CurrentSessionTransaction,
    routing_id: Annotated[int, Path(ge=1)],
    routing_operation_id: Annotated[int, Path(ge=1)],
) -> ResponseModel:
    await routing_service.delete_routing_operation(db, routing_id, routing_operation_id)
    return response_base.success()
