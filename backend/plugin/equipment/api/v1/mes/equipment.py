from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.equipment.enums import EquipmentStatus, EquipmentType, MoldStatus
from backend.plugin.equipment.schema.mold import (
    CavityStatusUpdate, CompleteMoldMaintenance, CreateCavityQuality, CreateMold,
    CreateMoldMaintenance, MoldCavityDetail, MoldCavityQualityDetail, MoldCostAnalysis,
    MoldCostEntryDetail, MoldDashboard, MoldDetail, MoldMaintenanceDetail, MoldMountDetail,
    MoldStatusUpdate, MoldUsageDetail, MountMold, UnmountMold,
)
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
from backend.plugin.equipment.service.mold_service import mold_service


router = APIRouter()
mold_view = [DependsJwtAuth, Depends(RequestPermission('mes:equipment:mold:view')), DependsRBAC]


@router.get('/molds/dashboard', dependencies=mold_view)
async def mold_dashboard(db: CurrentSession) -> ResponseSchemaModel[MoldDashboard]:
    return response_base.success(data=await mold_service.dashboard(db))


@router.get('/molds', dependencies=mold_view)
async def list_molds(
    db: CurrentSession, status: Annotated[MoldStatus | None, Query()] = None
) -> ResponseSchemaModel[list[MoldDetail]]:
    return response_base.success(data=await mold_service.list_molds(db, status))


@router.post('/molds', dependencies=[Depends(RequestPermission('mes:equipment:mold:config')), DependsRBAC])
async def create_mold(db: CurrentSessionTransaction, obj: CreateMold) -> ResponseSchemaModel[MoldDetail]:
    return response_base.success(data=await mold_service.create_mold(db, obj))


@router.put('/molds/{mold_id}/status', dependencies=[Depends(RequestPermission('mes:equipment:mold:config')), DependsRBAC])
async def update_mold_status(
    db: CurrentSessionTransaction, mold_id: Annotated[int, Path(ge=1)], obj: MoldStatusUpdate
) -> ResponseSchemaModel[MoldDetail]:
    return response_base.success(data=await mold_service.update_status(db, mold_id, obj))


@router.get('/molds/{mold_id}/cavities', dependencies=mold_view)
async def list_mold_cavities(
    db: CurrentSession, mold_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[MoldCavityDetail]]:
    return response_base.success(data=await mold_service.list_cavities(db, mold_id))


@router.put('/molds/cavities/{cavity_id}', dependencies=[Depends(RequestPermission('mes:equipment:mold:quality')), DependsRBAC])
async def update_mold_cavity(
    db: CurrentSessionTransaction, cavity_id: Annotated[int, Path(ge=1)], obj: CavityStatusUpdate
) -> ResponseSchemaModel[MoldCavityDetail]:
    return response_base.success(data=await mold_service.update_cavity(db, cavity_id, obj))


@router.post('/molds/{mold_id}/mount', dependencies=[Depends(RequestPermission('mes:equipment:mold:mount')), DependsRBAC])
async def mount_mold(
    db: CurrentSessionTransaction, mold_id: Annotated[int, Path(ge=1)], obj: MountMold
) -> ResponseSchemaModel[MoldMountDetail]:
    return response_base.success(data=await mold_service.mount(db, mold_id, obj))


@router.post('/molds/{mold_id}/unmount', dependencies=[Depends(RequestPermission('mes:equipment:mold:mount')), DependsRBAC])
async def unmount_mold(
    db: CurrentSessionTransaction, mold_id: Annotated[int, Path(ge=1)], obj: UnmountMold
) -> ResponseSchemaModel[MoldMountDetail]:
    return response_base.success(data=await mold_service.unmount(db, mold_id, obj))


@router.get('/molds/mounts/history', dependencies=mold_view)
async def list_mold_mounts(
    db: CurrentSession, mold_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[MoldMountDetail]]:
    return response_base.success(data=await mold_service.list_mounts(db, mold_id))


@router.get('/molds/usage/history', dependencies=mold_view)
async def list_mold_usage(
    db: CurrentSession, mold_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[MoldUsageDetail]]:
    return response_base.success(data=await mold_service.list_usage(db, mold_id))


@router.get('/molds/maintenance/orders', dependencies=mold_view)
async def list_mold_maintenance(
    db: CurrentSession, mold_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[MoldMaintenanceDetail]]:
    return response_base.success(data=await mold_service.list_maintenance(db, mold_id))


@router.post('/molds/{mold_id}/maintenance', dependencies=[Depends(RequestPermission('mes:equipment:mold:maintenance')), DependsRBAC])
async def create_mold_maintenance(
    db: CurrentSessionTransaction, mold_id: Annotated[int, Path(ge=1)], obj: CreateMoldMaintenance
) -> ResponseSchemaModel[MoldMaintenanceDetail]:
    return response_base.success(data=await mold_service.create_maintenance(db, mold_id, obj))


@router.post('/molds/maintenance/{order_id}/start', dependencies=[Depends(RequestPermission('mes:equipment:mold:maintenance')), DependsRBAC])
async def start_mold_maintenance(
    db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[MoldMaintenanceDetail]:
    return response_base.success(data=await mold_service.start_maintenance(db, order_id))


@router.post('/molds/maintenance/{order_id}/complete', dependencies=[Depends(RequestPermission('mes:equipment:mold:maintenance')), DependsRBAC])
async def complete_mold_maintenance(
    db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)], obj: CompleteMoldMaintenance
) -> ResponseSchemaModel[MoldMaintenanceDetail]:
    return response_base.success(data=await mold_service.complete_maintenance(db, order_id, obj))


@router.get('/molds/quality/history', dependencies=mold_view)
async def list_mold_quality(
    db: CurrentSession, mold_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[MoldCavityQualityDetail]]:
    return response_base.success(data=await mold_service.list_quality(db, mold_id))


@router.post('/molds/{mold_id}/quality', dependencies=[Depends(RequestPermission('mes:equipment:mold:quality')), DependsRBAC])
async def record_mold_quality(
    db: CurrentSessionTransaction, mold_id: Annotated[int, Path(ge=1)], obj: CreateCavityQuality
) -> ResponseSchemaModel[MoldCavityQualityDetail]:
    return response_base.success(data=await mold_service.record_cavity_quality(db, mold_id, obj))


@router.get('/molds/costs/ledger', dependencies=mold_view)
async def list_mold_costs(
    db: CurrentSession, mold_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[MoldCostEntryDetail]]:
    return response_base.success(data=await mold_service.list_costs(db, mold_id))


@router.get('/molds/{mold_id}/cost-analysis', dependencies=mold_view)
async def mold_cost_analysis(
    db: CurrentSession, mold_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[MoldCostAnalysis]:
    return response_base.success(data=await mold_service.cost_analysis(db, mold_id))


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
