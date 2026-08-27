from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.material.enums import MaterialStatus, MaterialType
from backend.plugin.material.schema.material import (
    CategoryDetail,
    CategoryTreeNode,
    CreateCategoryParam,
    CreateMaterialParam,
    CreateUnitParam,
    MaterialDetail,
    MaterialListItem,
    MaterialOption,
    MaterialStatusParam,
    UnitDetail,
    UpdateCategoryParam,
    UpdateMaterialParam,
    UpdateUnitParam,
    WarehouseOption,
)
from backend.plugin.material.service.material_service import material_service


router = APIRouter()


@router.get('/category/tree', dependencies=[DependsJwtAuth])
async def get_category_tree(db: CurrentSession) -> ResponseSchemaModel[list[CategoryTreeNode]]:
    data = await material_service.get_category_tree(db)
    return response_base.success(data=data)


@router.get('/category', dependencies=[DependsJwtAuth])
async def list_categories(db: CurrentSession) -> ResponseSchemaModel[list[CategoryDetail]]:
    data = await material_service.list_categories(db)
    return response_base.success(data=data)


@router.post(
    '/category',
    dependencies=[Depends(RequestPermission('mes:material:category')), DependsRBAC],
)
async def create_category(db: CurrentSessionTransaction, obj: CreateCategoryParam) -> ResponseSchemaModel[CategoryDetail]:
    data = await material_service.create_category(db, obj)
    return response_base.success(data=data)


@router.put(
    '/category/{category_id}',
    dependencies=[Depends(RequestPermission('mes:material:category')), DependsRBAC],
)
async def update_category(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: UpdateCategoryParam,
) -> ResponseSchemaModel[CategoryDetail]:
    data = await material_service.update_category(db, category_id, obj)
    return response_base.success(data=data)


@router.get('/unit', dependencies=[DependsJwtAuth])
async def list_units(
    db: CurrentSession,
    active_only: Annotated[bool, Query()] = True,
) -> ResponseSchemaModel[list[UnitDetail]]:
    data = await material_service.list_units(db, active_only=active_only)
    return response_base.success(data=data)


@router.post(
    '/unit',
    dependencies=[Depends(RequestPermission('mes:material:unit')), DependsRBAC],
)
async def create_unit(db: CurrentSessionTransaction, obj: CreateUnitParam) -> ResponseSchemaModel[UnitDetail]:
    data = await material_service.create_unit(db, obj)
    return response_base.success(data=data)


@router.put(
    '/unit/{unit_id}',
    dependencies=[Depends(RequestPermission('mes:material:unit')), DependsRBAC],
)
async def update_unit(
    db: CurrentSessionTransaction,
    unit_id: Annotated[int, Path(ge=1)],
    obj: UpdateUnitParam,
) -> ResponseSchemaModel[UnitDetail]:
    data = await material_service.update_unit(db, unit_id, obj)
    return response_base.success(data=data)


@router.get('/warehouse', dependencies=[DependsJwtAuth])
async def list_warehouse_options(db: CurrentSession) -> ResponseSchemaModel[list[WarehouseOption]]:
    warehouses = await material_service.list_warehouse_options(db)
    data = [
        WarehouseOption(id=item.id, code=item.warehouse_code, name=item.warehouse_name, status=item.status)
        for item in warehouses
    ]
    return response_base.success(data=data)


@router.get('/options', dependencies=[DependsJwtAuth])
async def get_material_options(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    material_type: Annotated[MaterialType | None, Query()] = None,
    purchasable: Annotated[bool | None, Query()] = None,
    producible: Annotated[bool | None, Query()] = None,
    sellable: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[list[MaterialOption]]:
    data = await material_service.list_options(db, keyword, material_type, purchasable, producible, sellable)
    return response_base.success(data=data)


@router.get(
    '',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def list_materials(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    material_type: Annotated[MaterialType | None, Query()] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[MaterialStatus | None, Query()] = None,
    batch_control: Annotated[bool | None, Query()] = None,
    purchasable: Annotated[bool | None, Query()] = None,
    producible: Annotated[bool | None, Query()] = None,
    sellable: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[PageData[MaterialListItem]]:
    data = await material_service.list_materials(
        db,
        keyword,
        material_type,
        category_id,
        status,
        batch_control,
        purchasable,
        producible,
        sellable,
    )
    return response_base.success(data=data)


@router.get('/{material_id}', dependencies=[DependsJwtAuth])
async def get_material(
    db: CurrentSession, material_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[MaterialDetail]:
    data = await material_service.get_material(db, material_id)
    return response_base.success(data=data)


@router.post(
    '',
    dependencies=[Depends(RequestPermission('mes:material:config')), DependsRBAC],
)
async def create_material(db: CurrentSessionTransaction, obj: CreateMaterialParam) -> ResponseSchemaModel[MaterialDetail]:
    material = await material_service.create_material(db, obj)
    data = await material_service.get_material(db, material.id)
    return response_base.success(data=data)


@router.put(
    '/{material_id}',
    dependencies=[Depends(RequestPermission('mes:material:config')), DependsRBAC],
)
async def update_material(
    db: CurrentSessionTransaction,
    material_id: Annotated[int, Path(ge=1)],
    obj: UpdateMaterialParam,
) -> ResponseSchemaModel[MaterialDetail]:
    await material_service.update_material(db, material_id, obj)
    data = await material_service.get_material(db, material_id)
    return response_base.success(data=data)


@router.put(
    '/{material_id}/status',
    dependencies=[Depends(RequestPermission('mes:material:status')), DependsRBAC],
)
async def update_material_status(
    db: CurrentSessionTransaction,
    material_id: Annotated[int, Path(ge=1)],
    obj: MaterialStatusParam,
) -> ResponseSchemaModel[MaterialDetail]:
    await material_service.update_material_status(db, material_id, obj.status)
    data = await material_service.get_material(db, material_id)
    return response_base.success(data=data)
