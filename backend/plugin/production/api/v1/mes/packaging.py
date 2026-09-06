from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.production.model import (
    PackagingInspection, PackagingLabelPrint, PackagingSpecification, PackagingWeightRecord,
)
from backend.plugin.production.schema.packaging import (
    CreateHandlingUnit, CreatePackagingSpecification, CreatePackagingTask, InspectHandlingUnit,
    PackagingDashboard, PackagingHandlingUnitDetail, PackagingTaskDetail, PrintPackagingLabel,
    RecordPackagingWeight, ReopenHandlingUnit, ScanPackagingItem, SealHandlingUnit,
    SetPackagingSpecificationStatus,
)
from backend.plugin.production.service import packaging_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:packaging:view')), DependsRBAC]


@router.get('/dashboard', dependencies=view_dependencies)
async def dashboard(db: CurrentSession) -> ResponseSchemaModel[PackagingDashboard]:
    return response_base.success(data=await packaging_service.dashboard(db))


@router.get('/specifications', dependencies=view_dependencies)
async def list_specifications(
    db: CurrentSession,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[str | None, Query(max_length=20)] = None,
) -> ResponseSchemaModel[list[PackagingSpecification]]:
    return response_base.success(data=await packaging_service.list_specifications(db, material_id, status))


@router.post(
    '/specifications',
    dependencies=[Depends(RequestPermission('mes:packaging:manage')), DependsRBAC],
)
async def create_specification(
    db: CurrentSessionTransaction, obj: CreatePackagingSpecification
) -> ResponseSchemaModel[PackagingSpecification]:
    return response_base.success(data=await packaging_service.create_specification(db, obj))


@router.put(
    '/specifications/{spec_id}/status',
    dependencies=[Depends(RequestPermission('mes:packaging:manage')), DependsRBAC],
)
async def set_specification_status(
    db: CurrentSessionTransaction,
    spec_id: Annotated[int, Path(ge=1)],
    obj: SetPackagingSpecificationStatus,
) -> ResponseSchemaModel[PackagingSpecification]:
    return response_base.success(data=await packaging_service.set_specification_status(db, spec_id, obj.status))


@router.get('/tasks', dependencies=view_dependencies)
async def list_tasks(
    db: CurrentSession, status: Annotated[str | None, Query(max_length=30)] = None
) -> ResponseSchemaModel[list[PackagingTaskDetail]]:
    return response_base.success(data=await packaging_service.list_tasks(db, status))


@router.post('/tasks', dependencies=[Depends(RequestPermission('mes:packaging:manage')), DependsRBAC])
async def create_task(
    db: CurrentSessionTransaction, obj: CreatePackagingTask
) -> ResponseSchemaModel[PackagingTaskDetail]:
    return response_base.success(data=await packaging_service.create_task(db, obj))


@router.get('/tasks/{task_id}', dependencies=view_dependencies)
async def get_task(
    db: CurrentSession, task_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[PackagingTaskDetail]:
    return response_base.success(data=await packaging_service.get_task(db, task_id))


@router.post('/tasks/{task_id}/release', dependencies=[Depends(RequestPermission('mes:packaging:manage')), DependsRBAC])
async def release_task(
    db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[PackagingTaskDetail]:
    return response_base.success(data=await packaging_service.release_task(db, task_id))


@router.post('/tasks/{task_id}/start', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def start_task(
    db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[PackagingTaskDetail]:
    return response_base.success(data=await packaging_service.start_task(db, task_id))


@router.post('/tasks/{task_id}/handling-units', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def create_handling_unit(
    db: CurrentSessionTransaction,
    task_id: Annotated[int, Path(ge=1)],
    obj: CreateHandlingUnit,
) -> ResponseSchemaModel[PackagingHandlingUnitDetail]:
    return response_base.success(data=await packaging_service.create_handling_unit(db, task_id, obj))


@router.post('/tasks/{task_id}/release-to-stock', dependencies=[Depends(RequestPermission('mes:packaging:release')), DependsRBAC])
async def release_to_stock(
    db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[PackagingTaskDetail]:
    return response_base.success(data=await packaging_service.release_to_stock(db, task_id))


@router.get('/handling-units/by-code/{hu_code}', dependencies=view_dependencies)
async def get_handling_unit(
    db: CurrentSession, hu_code: Annotated[str, Path(min_length=1, max_length=120)]
) -> ResponseSchemaModel[PackagingHandlingUnitDetail]:
    return response_base.success(data=await packaging_service.get_handling_unit(db, hu_code))


@router.post('/handling-units/{hu_id}/scan', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def scan_item(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: ScanPackagingItem,
) -> ResponseSchemaModel[PackagingHandlingUnitDetail]:
    return response_base.success(data=await packaging_service.scan_item(db, hu_id, obj))


@router.post('/handling-units/{hu_id}/weight', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def record_weight(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: RecordPackagingWeight,
) -> ResponseSchemaModel[PackagingWeightRecord]:
    return response_base.success(data=await packaging_service.record_weight(db, hu_id, obj))


@router.post('/handling-units/{hu_id}/seal', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def seal_handling_unit(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: SealHandlingUnit,
) -> ResponseSchemaModel[PackagingHandlingUnitDetail]:
    return response_base.success(data=await packaging_service.seal_handling_unit(db, hu_id, obj))


@router.post('/handling-units/{hu_id}/reopen', dependencies=[Depends(RequestPermission('mes:packaging:manage')), DependsRBAC])
async def reopen_handling_unit(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: ReopenHandlingUnit,
) -> ResponseSchemaModel[PackagingHandlingUnitDetail]:
    return response_base.success(data=await packaging_service.reopen_handling_unit(db, hu_id, obj))


@router.post('/handling-units/{hu_id}/inspection', dependencies=[Depends(RequestPermission('mes:packaging:inspect')), DependsRBAC])
async def inspect_handling_unit(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: InspectHandlingUnit,
) -> ResponseSchemaModel[PackagingInspection]:
    return response_base.success(data=await packaging_service.inspect_handling_unit(db, hu_id, obj))


@router.post('/handling-units/{hu_id}/labels', dependencies=[Depends(RequestPermission('mes:packaging:execute')), DependsRBAC])
async def print_label(
    db: CurrentSessionTransaction,
    hu_id: Annotated[int, Path(ge=1)],
    obj: PrintPackagingLabel,
) -> ResponseSchemaModel[PackagingLabelPrint]:
    return response_base.success(data=await packaging_service.print_label(db, hu_id, obj))
