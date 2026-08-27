from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.supplier.enums import CooperationStatus, SupplierQualityStatus, SupplierStatus
from backend.plugin.supplier.schema.supplier import (
    CreateSupplierCategoryParam,
    CreateSupplierContactParam,
    CreateSupplierMaterialParam,
    CreateSupplierParam,
    SupplierCategoryDetail,
    SupplierCategoryStatusParam,
    SupplierCategoryTreeNode,
    SupplierContactDetail,
    SupplierContactStatusParam,
    SupplierCooperationParam,
    SupplierDetail,
    SupplierListItem,
    SupplierMaterialDetail,
    SupplierMaterialStatusParam,
    SupplierOption,
    SupplierQualityParam,
    SupplierStatusParam,
    UpdateSupplierCategoryParam,
    UpdateSupplierContactParam,
    UpdateSupplierMaterialParam,
    UpdateSupplierParam,
)
from backend.plugin.supplier.service import supplier_service


router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('erp:supplier:view')), DependsRBAC]


@router.get('/category/tree', dependencies=view_dependencies)
async def get_category_tree(db: CurrentSession) -> ResponseSchemaModel[list[SupplierCategoryTreeNode]]:
    return response_base.success(data=await supplier_service.get_category_tree(db))


@router.get('/category', dependencies=view_dependencies)
async def list_categories(db: CurrentSession) -> ResponseSchemaModel[list[SupplierCategoryDetail]]:
    return response_base.success(data=await supplier_service.list_categories(db))


@router.post('/category', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC])
async def create_category(
    db: CurrentSessionTransaction, obj: CreateSupplierCategoryParam
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.create_category(db, obj))


@router.put('/category/{category_id}', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC])
async def update_category(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierCategoryParam,
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.update_category(db, category_id, obj))


@router.put(
    '/category/{category_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC]
)
async def update_category_status(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: SupplierCategoryStatusParam,
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.update_category_status(db, category_id, obj.status))


@router.get('/options', dependencies=view_dependencies)
async def supplier_options(
    db: CurrentSession,
    material_id: Annotated[int | None, Query(ge=1)] = None,
) -> ResponseSchemaModel[list[SupplierOption]]:
    return response_base.success(data=await supplier_service.supplier_options(db, material_id))


@router.get('', dependencies=[*view_dependencies, DependsPagination])
async def list_suppliers(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SupplierStatus | None, Query()] = None,
    cooperation_status: Annotated[CooperationStatus | None, Query()] = None,
    quality_status: Annotated[SupplierQualityStatus | None, Query()] = None,
    preferred: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[PageData[SupplierListItem]]:
    data = await supplier_service.list_suppliers(
        db, keyword, category_id, status, cooperation_status, quality_status, preferred
    )
    return response_base.success(data=data)


@router.get('/{supplier_id}', dependencies=view_dependencies)
async def get_supplier(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.get_supplier(db, supplier_id))


@router.post('', dependencies=[Depends(RequestPermission('erp:supplier:config')), DependsRBAC])
async def create_supplier(db: CurrentSessionTransaction, obj: CreateSupplierParam) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.create_supplier(db, obj))


@router.put('/{supplier_id}', dependencies=[Depends(RequestPermission('erp:supplier:config')), DependsRBAC])
async def update_supplier(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier(db, supplier_id, obj))


@router.put('/{supplier_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:status')), DependsRBAC])
async def update_supplier_status(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierStatusParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier_status(db, supplier_id, obj.status))


@router.put(
    '/{supplier_id}/cooperation', dependencies=[Depends(RequestPermission('erp:supplier:cooperation')), DependsRBAC]
)
async def update_supplier_cooperation(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierCooperationParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(
        data=await supplier_service.update_supplier_cooperation(db, supplier_id, obj.cooperation_status)
    )


@router.put('/{supplier_id}/quality', dependencies=[Depends(RequestPermission('erp:supplier:quality')), DependsRBAC])
async def update_supplier_quality(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierQualityParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier_quality(db, supplier_id, obj.quality_status))


@router.get('/{supplier_id}/contacts', dependencies=view_dependencies)
async def list_contacts(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[SupplierContactDetail]]:
    return response_base.success(data=await supplier_service.list_contacts(db, supplier_id))


@router.post(
    '/{supplier_id}/contacts', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def create_contact(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: CreateSupplierContactParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.create_contact(db, supplier_id, obj))


@router.put('/contacts/{contact_id}', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC])
async def update_contact(
    db: CurrentSessionTransaction,
    contact_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierContactParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.update_contact(db, contact_id, obj))


@router.put(
    '/contacts/{contact_id}/primary', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def set_contact_primary(
    db: CurrentSessionTransaction, contact_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.set_contact_primary(db, contact_id))


@router.put(
    '/contacts/{contact_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def update_contact_status(
    db: CurrentSessionTransaction,
    contact_id: Annotated[int, Path(ge=1)],
    obj: SupplierContactStatusParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.update_contact_status(db, contact_id, obj.status))


@router.get('/{supplier_id}/materials', dependencies=view_dependencies)
async def list_supplier_materials(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[SupplierMaterialDetail]]:
    return response_base.success(data=await supplier_service.list_supplier_materials(db, supplier_id))


@router.post(
    '/{supplier_id}/materials', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def create_supplier_material(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: CreateSupplierMaterialParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.create_supplier_material(db, supplier_id, obj))


@router.put(
    '/materials/{relation_id}', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def update_supplier_material(
    db: CurrentSessionTransaction,
    relation_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierMaterialParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.update_supplier_material(db, relation_id, obj))


@router.put(
    '/materials/{relation_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def update_supplier_material_status(
    db: CurrentSessionTransaction,
    relation_id: Annotated[int, Path(ge=1)],
    obj: SupplierMaterialStatusParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.update_supplier_material_status(db, relation_id, obj.status))
