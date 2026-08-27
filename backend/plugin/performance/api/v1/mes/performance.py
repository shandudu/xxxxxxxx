from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.performance.enums import MetricGrain
from backend.plugin.performance.schema.performance import (
    CycleAnalysis,
    DowntimePareto,
    EquipmentReliability,
    PerformanceDashboard,
    PerformanceSnapshotDetail,
    PerformanceTargetDetail,
    PerformanceTargetInput,
    PerformanceTrendPoint,
    RebuildSnapshots,
    SnapshotRebuildResult,
    WorkCenterPerformance,
)
from backend.plugin.performance.service import performance_service


router = APIRouter()
view_dependencies = [
    DependsJwtAuth,
    Depends(RequestPermission('mes:performance:view')),
    DependsRBAC,
]


@router.get('/dashboard', dependencies=view_dependencies)
async def dashboard(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[PerformanceDashboard]:
    return response_base.success(
        data=await performance_service.dashboard(db, start_date, end_date, work_center_id)
    )


@router.get('/work-centers', dependencies=view_dependencies)
async def work_centers(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[list[WorkCenterPerformance]]:
    return response_base.success(
        data=await performance_service.work_centers(db, start_date, end_date, work_center_id)
    )


@router.get('/trend', dependencies=view_dependencies)
async def trend(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    grain: MetricGrain = Query(default=MetricGrain.DAY),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[list[PerformanceTrendPoint]]:
    return response_base.success(
        data=await performance_service.trend(
            db, start_date, end_date, grain, work_center_id
        )
    )


@router.get('/equipment-reliability', dependencies=view_dependencies)
async def equipment_reliability(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    equipment_id: int | None = Query(default=None, ge=1),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[list[EquipmentReliability]]:
    return response_base.success(
        data=await performance_service.equipment_reliability(
            db, start_date, end_date, equipment_id, work_center_id
        )
    )


@router.get('/cycle-analysis', dependencies=view_dependencies)
async def cycle_analysis(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[list[CycleAnalysis]]:
    return response_base.success(
        data=await performance_service.cycle_analysis(
            db, start_date, end_date, work_center_id
        )
    )


@router.get('/downtime-pareto', dependencies=view_dependencies)
async def downtime_pareto(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    work_center_id: int | None = Query(default=None, ge=1),
    top_n: int = Query(default=10, ge=1, le=50),
) -> ResponseSchemaModel[list[DowntimePareto]]:
    return response_base.success(
        data=await performance_service.downtime_pareto(
            db, start_date, end_date, work_center_id, top_n
        )
    )


@router.get('/targets', dependencies=view_dependencies)
async def targets(db: CurrentSession) -> ResponseSchemaModel[list[PerformanceTargetDetail]]:
    return response_base.success(data=await performance_service.targets(db))


@router.put(
    '/targets/{work_center_id}',
    dependencies=[Depends(RequestPermission('mes:performance:target')), DependsRBAC],
)
async def upsert_target(
    db: CurrentSessionTransaction,
    work_center_id: Annotated[int, Path(ge=1)],
    obj: PerformanceTargetInput,
) -> ResponseSchemaModel[PerformanceTargetDetail]:
    return response_base.success(
        data=await performance_service.upsert_target(db, work_center_id, obj)
    )


@router.get('/snapshots', dependencies=view_dependencies)
async def snapshots(
    db: CurrentSession,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    work_center_id: int | None = Query(default=None, ge=1),
) -> ResponseSchemaModel[list[PerformanceSnapshotDetail]]:
    return response_base.success(
        data=await performance_service.snapshots(db, start_date, end_date, work_center_id)
    )


@router.post(
    '/snapshots/rebuild',
    dependencies=[Depends(RequestPermission('mes:performance:rebuild')), DependsRBAC],
)
async def rebuild_snapshots(
    db: CurrentSessionTransaction,
    obj: RebuildSnapshots,
) -> ResponseSchemaModel[SnapshotRebuildResult]:
    return response_base.success(data=await performance_service.rebuild_snapshots(db, obj))
