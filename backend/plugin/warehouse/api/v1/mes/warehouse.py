from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.warehouse.schema.warehouse import (
    AreaDetail,
    CreateAreaConfig,
    CreateLocationConfig,
    CreateWarehouseConfig,
    LocationDetail,
    LocationGenerateConfig,
    LocationGeneratePreview,
    LocationMoveConfig,
    LocationStatusConfig,
    UpdateAreaConfig,
    UpdateLocationConfig,
    UpdateWarehouseConfig,
    WarehouseDetail,
    WarehouseTree,
)
from backend.plugin.warehouse.service.warehouse_service import warehouse_service


router = APIRouter()


@router.get('', dependencies=[DependsJwtAuth])
async def list_warehouses(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    warehouse_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[list[WarehouseDetail]]:
    data = await warehouse_service.list_warehouses(db, keyword, warehouse_type, status)
    return response_base.success(data=data)


@router.get('/{warehouse_id}', dependencies=[DependsJwtAuth])
async def get_warehouse(
    db: CurrentSession, warehouse_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[WarehouseDetail]:
    data = await warehouse_service.get_warehouse(db, warehouse_id)
    return response_base.success(data=data)


@router.post(
    '/config',
    dependencies=[Depends(RequestPermission('mes:warehouse:config')), DependsRBAC],
)
async def create_warehouse(
    db: CurrentSessionTransaction, obj: CreateWarehouseConfig
) -> ResponseSchemaModel[WarehouseDetail]:
    data = await warehouse_service.create_warehouse(db, obj)
    return response_base.success(data=data)


@router.put(
    '/{warehouse_id}/config',
    dependencies=[Depends(RequestPermission('mes:warehouse:config')), DependsRBAC],
)
async def update_warehouse(
    db: CurrentSessionTransaction,
    warehouse_id: Annotated[int, Path(ge=1)],
    obj: UpdateWarehouseConfig,
) -> ResponseSchemaModel[WarehouseDetail]:
    data = await warehouse_service.update_warehouse(db, warehouse_id, obj)
    return response_base.success(data=data)


@router.get('/{warehouse_id}/areas', dependencies=[DependsJwtAuth])
async def list_areas(
    db: CurrentSession, warehouse_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[AreaDetail]]:
    data = await warehouse_service.list_areas(db, warehouse_id)
    return response_base.success(data=data)


@router.post(
    '/area/config',
    dependencies=[Depends(RequestPermission('mes:warehouse:config')), DependsRBAC],
)
async def create_area(
    db: CurrentSessionTransaction, obj: CreateAreaConfig
) -> ResponseSchemaModel[AreaDetail]:
    data = await warehouse_service.create_area(db, obj)
    return response_base.success(data=data)


@router.put(
    '/area/{area_id}/config',
    dependencies=[Depends(RequestPermission('mes:warehouse:config')), DependsRBAC],
)
async def update_area(
    db: CurrentSessionTransaction,
    area_id: Annotated[int, Path(ge=1)],
    obj: UpdateAreaConfig,
) -> ResponseSchemaModel[AreaDetail]:
    data = await warehouse_service.update_area(db, area_id, obj)
    return response_base.success(data=data)


@router.get('/{warehouse_id}/tree', dependencies=[DependsJwtAuth])
async def get_warehouse_tree(
    db: CurrentSession, warehouse_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[WarehouseTree]:
    data = await warehouse_service.get_tree(db, warehouse_id)
    return response_base.success(data=data)


@router.get('/{warehouse_id}/locations', dependencies=[DependsJwtAuth])
async def list_locations(
    db: CurrentSession,
    warehouse_id: Annotated[int, Path(ge=1)],
    area_id: Annotated[int | None, Query(ge=1)] = None,
    keyword: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[list[LocationDetail]]:
    data = await warehouse_service.list_locations(db, warehouse_id, area_id, keyword)
    return response_base.success(data=data)


@router.get('/location/{location_id}', dependencies=[DependsJwtAuth])
async def get_location(
    db: CurrentSession, location_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[LocationDetail]:
    data = await warehouse_service.get_location(db, location_id)
    return response_base.success(data=data)


@router.get('/{warehouse_id}/locations/search', dependencies=[DependsJwtAuth])
async def search_locations(
    db: CurrentSession,
    warehouse_id: Annotated[int, Path(ge=1)],
    keyword: Annotated[str, Query(min_length=1)],
) -> ResponseSchemaModel[list[dict]]:
    data = await warehouse_service.search_locations(db, warehouse_id, keyword)
    return response_base.success(data=data)


@router.post(
    '/location/config',
    dependencies=[Depends(RequestPermission('mes:location:config')), DependsRBAC],
)
async def create_location(
    db: CurrentSessionTransaction, obj: CreateLocationConfig
) -> ResponseSchemaModel[LocationDetail]:
    data = await warehouse_service.create_location(db, obj)
    return response_base.success(data=data)


@router.put(
    '/location/{location_id}/config',
    dependencies=[Depends(RequestPermission('mes:location:config')), DependsRBAC],
)
async def update_location(
    db: CurrentSessionTransaction,
    location_id: Annotated[int, Path(ge=1)],
    obj: UpdateLocationConfig,
) -> ResponseSchemaModel[LocationDetail]:
    data = await warehouse_service.update_location(db, location_id, obj)
    return response_base.success(data=data)


@router.put(
    '/location/{location_id}/move',
    dependencies=[Depends(RequestPermission('mes:location:config')), DependsRBAC],
)
async def move_location(
    db: CurrentSessionTransaction,
    location_id: Annotated[int, Path(ge=1)],
    obj: LocationMoveConfig,
) -> ResponseSchemaModel[LocationDetail]:
    data = await warehouse_service.move_location(db, location_id, obj)
    return response_base.success(data=data)


@router.put(
    '/location/{location_id}/status',
    dependencies=[Depends(RequestPermission('mes:location:status')), DependsRBAC],
)
async def update_location_status(
    db: CurrentSessionTransaction,
    location_id: Annotated[int, Path(ge=1)],
    obj: LocationStatusConfig,
) -> ResponseSchemaModel[LocationDetail]:
    data = await warehouse_service.update_location_status(db, location_id, obj)
    return response_base.success(data=data)


@router.post(
    '/location/generate-preview',
    dependencies=[Depends(RequestPermission('mes:location:generate')), DependsRBAC],
)
async def preview_generate_locations(
    db: CurrentSession, obj: LocationGenerateConfig
) -> ResponseSchemaModel[LocationGeneratePreview]:
    data = await warehouse_service.preview_generate(db, obj)
    return response_base.success(data=data)


@router.post(
    '/location/generate',
    dependencies=[Depends(RequestPermission('mes:location:generate')), DependsRBAC],
)
async def generate_locations(
    db: CurrentSessionTransaction, obj: LocationGenerateConfig
) -> ResponseModel:
    locations = await warehouse_service.generate_locations(db, obj)
    return response_base.success(data={'count': len(locations)})
