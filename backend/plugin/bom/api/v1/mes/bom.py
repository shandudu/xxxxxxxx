from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.schema.bom import (
    BomCompareResult,
    BomDetail,
    BomItemDetail,
    BomListItem,
    BomOption,
    BomTree,
    BomValidationResult,
    CalculateBomParam,
    CopyBomParam,
    CreateBomItemParam,
    CreateBomParam,
    MaterialRequirement,
    UpdateBomItemParam,
    UpdateBomParam,
)
from backend.plugin.bom.service.bom_service import bom_service


router = APIRouter()


@router.get('/compare', dependencies=[DependsJwtAuth])
async def compare_boms(
    db: CurrentSession,
    source_bom_id: Annotated[int, Query(ge=1)],
    target_bom_id: Annotated[int, Query(ge=1)],
) -> ResponseSchemaModel[BomCompareResult]:
    data = await bom_service.compare(db, source_bom_id, target_bom_id)
    return response_base.success(data=data)


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_bom_options(
    db: CurrentSession,
    product_material_id: Annotated[int, Query(ge=1)],
    effective_date: Annotated[datetime | None, Query()] = None,
) -> ResponseSchemaModel[list[BomOption]]:
    data = await bom_service.list_options(db, product_material_id, effective_date)
    return response_base.success(data=data)


@router.get('/default', dependencies=[DependsJwtAuth])
async def get_default_bom(
    db: CurrentSession,
    product_material_id: Annotated[int, Query(ge=1)],
    effective_date: Annotated[datetime | None, Query()] = None,
) -> ResponseSchemaModel[BomOption]:
    data = await bom_service.get_default(db, product_material_id, effective_date)
    return response_base.success(data=data)


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_boms(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    product_material_id: Annotated[int | None, Query(ge=1)] = None,
    product_keyword: Annotated[str | None, Query()] = None,
    status: Annotated[BomStatus | None, Query()] = None,
    is_default: Annotated[bool | None, Query()] = None,
    effective_date: Annotated[datetime | None, Query()] = None,
) -> ResponseSchemaModel[PageData[BomListItem]]:
    data = await bom_service.list_boms(
        db, keyword, product_keyword, product_material_id, status, is_default, effective_date
    )
    return response_base.success(data=data)


@router.get('/{bom_id}', dependencies=[DependsJwtAuth])
async def get_bom(
    db: CurrentSession, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomDetail]:
    data = await bom_service.get_bom(db, bom_id)
    return response_base.success(data=data)


@router.post(
    '',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def create_bom(db: CurrentSessionTransaction, obj: CreateBomParam) -> ResponseSchemaModel[BomDetail]:
    bom = await bom_service.create_bom(db, obj)
    data = await bom_service.get_bom(db, bom.id)
    return response_base.success(data=data)


@router.put(
    '/{bom_id}',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def update_bom(
    db: CurrentSessionTransaction,
    bom_id: Annotated[int, Path(ge=1)],
    obj: UpdateBomParam,
) -> ResponseSchemaModel[BomDetail]:
    await bom_service.update_bom(db, bom_id, obj)
    data = await bom_service.get_bom(db, bom_id)
    return response_base.success(data=data)


@router.post(
    '/{bom_id}/copy',
    dependencies=[Depends(RequestPermission('mes:bom:copy')), DependsRBAC],
)
async def copy_bom(
    db: CurrentSessionTransaction,
    bom_id: Annotated[int, Path(ge=1)],
    obj: CopyBomParam,
) -> ResponseSchemaModel[BomDetail]:
    data = await bom_service.copy_bom(db, bom_id, obj)
    return response_base.success(data=data)


@router.post(
    '/{bom_id}/validate',
    dependencies=[Depends(RequestPermission('mes:bom:validate')), DependsRBAC],
)
async def validate_bom(
    db: CurrentSession, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomValidationResult]:
    data = await bom_service.validate_bom(db, bom_id)
    return response_base.success(data=data)


@router.post(
    '/{bom_id}/activate',
    dependencies=[Depends(RequestPermission('mes:bom:activate')), DependsRBAC],
)
async def activate_bom(
    db: CurrentSessionTransaction, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomDetail]:
    await bom_service.activate_bom(db, bom_id)
    data = await bom_service.get_bom(db, bom_id)
    return response_base.success(data=data)


@router.post(
    '/{bom_id}/deactivate',
    dependencies=[Depends(RequestPermission('mes:bom:deactivate')), DependsRBAC],
)
async def deactivate_bom(
    db: CurrentSessionTransaction, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomDetail]:
    await bom_service.deactivate_bom(db, bom_id)
    data = await bom_service.get_bom(db, bom_id)
    return response_base.success(data=data)


@router.put(
    '/{bom_id}/default',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def set_default_bom(
    db: CurrentSessionTransaction, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomDetail]:
    await bom_service.set_default_bom(db, bom_id)
    data = await bom_service.get_bom(db, bom_id)
    return response_base.success(data=data)


@router.get('/{bom_id}/tree', dependencies=[DependsJwtAuth])
async def get_bom_tree(
    db: CurrentSession, bom_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[BomTree]:
    data = await bom_service.get_tree(db, bom_id)
    return response_base.success(data=data)


@router.post('/{bom_id}/calculate', dependencies=[DependsJwtAuth])
async def calculate_bom(
    db: CurrentSession,
    bom_id: Annotated[int, Path(ge=1)],
    obj: CalculateBomParam,
) -> ResponseSchemaModel[list[MaterialRequirement]]:
    data = await bom_service.calculate(db, bom_id, obj)
    return response_base.success(data=data)


@router.post(
    '/{bom_id}/items',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def add_bom_item(
    db: CurrentSessionTransaction,
    bom_id: Annotated[int, Path(ge=1)],
    obj: CreateBomItemParam,
) -> ResponseSchemaModel[BomItemDetail]:
    item = await bom_service.add_item(db, bom_id, obj)
    data = await bom_service._item_detail(db, item)
    return response_base.success(data=data)


@router.put(
    '/{bom_id}/items/{item_id}',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def update_bom_item(
    db: CurrentSessionTransaction,
    bom_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
    obj: UpdateBomItemParam,
) -> ResponseSchemaModel[BomItemDetail]:
    item = await bom_service.update_item(db, bom_id, item_id, obj)
    data = await bom_service._item_detail(db, item)
    return response_base.success(data=data)


@router.delete(
    '/{bom_id}/items/{item_id}',
    dependencies=[Depends(RequestPermission('mes:bom:config')), DependsRBAC],
)
async def delete_bom_item(
    db: CurrentSessionTransaction,
    bom_id: Annotated[int, Path(ge=1)],
    item_id: Annotated[int, Path(ge=1)],
) -> ResponseModel:
    await bom_service.delete_item(db, bom_id, item_id)
    return response_base.success()
