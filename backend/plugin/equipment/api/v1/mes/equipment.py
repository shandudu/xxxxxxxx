from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.equipment.enums import EquipmentStatus, EquipmentType
from backend.plugin.equipment.schema.equipment import (
    CreateEquipmentCategoryParam,
    CreateEquipmentParam,
    EquipmentCategoryDetail,
    EquipmentCategoryTreeNode,
    EquipmentDetail,
    EquipmentEnabledParam,
    EquipmentListItem,
    EquipmentOption,
    EquipmentStatusParam,
    UpdateEquipmentCategoryParam,
    UpdateEquipmentParam,
)
from backend.plugin.equipment.service.equipment_service import equipment_service


router = APIRouter()


@router.get('/category/tree', dependencies=[DependsJwtAuth])
async def get_category_tree(db: CurrentSession) -> ResponseSchemaModel[list[EquipmentCategoryTreeNode]]:
    return response_base.success(data=await equipment_service.get_category_tree(db))


@router.get('/category', dependencies=[DependsJwtAuth])
async def list_categories(db: CurrentSession) -> ResponseSchemaModel[list[EquipmentCategoryDetail]]:
    return response_base.success(data=await equipment_service.list_categories(db))


@router.post(
    '/category',
    dependencies=[Depends(RequestPermission('mes:equipment:category')), DependsRBAC],
)
async def create_category(
    db: CurrentSessionTransaction, obj: CreateEquipmentCategoryParam
) -> ResponseSchemaModel[EquipmentCategoryDetail]:
    return response_base.success(data=await equipment_service.create_category(db, obj))


@router.put(
    '/category/{category_id}',
    dependencies=[Depends(RequestPermission('mes:equipment:category')), DependsRBAC],
)
async def update_category(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: UpdateEquipmentCategoryParam,
) -> ResponseSchemaModel[EquipmentCategoryDetail]:
    return response_base.success(data=await equipment_service.update_category(db, category_id, obj))


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_options(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    equipment_type: Annotated[EquipmentType | None, Query()] = None,
    production_enabled: Annotated[bool | None, Query()] = None,
    maintenance_enabled: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[list[EquipmentOption]]:
    data = await equipment_service.list_options(db, keyword, equipment_type, production_enabled, maintenance_enabled)
    return response_base.success(data=data)


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_equipment(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    equipment_type: Annotated[EquipmentType | None, Query()] = None,
    status: Annotated[EquipmentStatus | None, Query()] = None,
    enabled: Annotated[bool | None, Query()] = None,
    production_enabled: Annotated[bool | None, Query()] = None,
    data_collection_enabled: Annotated[bool | None, Query()] = None,
    maintenance_enabled: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[PageData[EquipmentListItem]]:
    data = await equipment_service.list_equipment(
        db,
        keyword,
        category_id,
        equipment_type,
        status,
        enabled,
        production_enabled,
        data_collection_enabled,
        maintenance_enabled,
    )
    return response_base.success(data=data)


@router.get('/{equipment_id}', dependencies=[DependsJwtAuth])
async def get_equipment(
    db: CurrentSession, equipment_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[EquipmentDetail]:
    return response_base.success(data=await equipment_service.get_equipment(db, equipment_id))


@router.post(
    '',
    dependencies=[Depends(RequestPermission('mes:equipment:config')), DependsRBAC],
)
async def create_equipment(
    db: CurrentSessionTransaction, obj: CreateEquipmentParam
) -> ResponseSchemaModel[EquipmentDetail]:
    equipment = await equipment_service.create_equipment(db, obj)
    return response_base.success(data=await equipment_service.get_equipment(db, equipment.id))


@router.put(
    '/{equipment_id}',
    dependencies=[Depends(RequestPermission('mes:equipment:config')), DependsRBAC],
)
async def update_equipment(
    db: CurrentSessionTransaction,
    equipment_id: Annotated[int, Path(ge=1)],
    obj: UpdateEquipmentParam,
) -> ResponseSchemaModel[EquipmentDetail]:
    await equipment_service.update_equipment(db, equipment_id, obj)
    return response_base.success(data=await equipment_service.get_equipment(db, equipment_id))


@router.put(
    '/{equipment_id}/enabled',
    dependencies=[Depends(RequestPermission('mes:equipment:enabled')), DependsRBAC],
)
async def update_enabled(
    db: CurrentSessionTransaction,
    equipment_id: Annotated[int, Path(ge=1)],
    obj: EquipmentEnabledParam,
) -> ResponseSchemaModel[EquipmentDetail]:
    await equipment_service.update_enabled(db, equipment_id, obj.enabled)
    return response_base.success(data=await equipment_service.get_equipment(db, equipment_id))


@router.put(
    '/{equipment_id}/status',
    dependencies=[Depends(RequestPermission('mes:equipment:status')), DependsRBAC],
)
async def update_status(
    db: CurrentSessionTransaction,
    equipment_id: Annotated[int, Path(ge=1)],
    obj: EquipmentStatusParam,
) -> ResponseSchemaModel[EquipmentDetail]:
    await equipment_service.update_status(db, equipment_id, obj.status)
    return response_base.success(data=await equipment_service.get_equipment(db, equipment_id))
