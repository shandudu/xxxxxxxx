from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.trace.enums import LotStatus, SerialStatus, TraceObjectType, TraceRuleType
from backend.plugin.trace.schema.trace import (
    CreateMaterialLotParam,
    CreateTraceCodeRuleParam,
    CreateTraceRelationParam,
    GenerateMaterialSerialParam,
    LotDetail,
    LotMergeParam,
    LotSplitParam,
    LotStatusParam,
    MaterialSerialDetail,
    MaterialSerialGenerateResult,
    MaterialSerialListItem,
    MaterialTraceRuleDetail,
    MaterialTraceRuleParam,
    SerialStatusParam,
    TraceCodePreviewParam,
    TraceCodeRuleDetail,
    TraceNode,
    TraceRelationDetail,
    UpdateTraceCodeRuleParam,
)
from backend.plugin.trace.service.trace_service import trace_service


router = APIRouter()


@router.get('/code-rule', dependencies=[DependsJwtAuth])
async def list_code_rules(
    db: CurrentSession,
    rule_type: Annotated[TraceRuleType | None, Query()] = None,
) -> ResponseSchemaModel[list[TraceCodeRuleDetail]]:
    return response_base.success(data=await trace_service.list_rules(db, rule_type))


@router.post(
    '/code-rule',
    dependencies=[Depends(RequestPermission('mes:trace:rule:config')), DependsRBAC],
)
async def create_code_rule(
    db: CurrentSessionTransaction, obj: CreateTraceCodeRuleParam
) -> ResponseSchemaModel[TraceCodeRuleDetail]:
    return response_base.success(data=await trace_service.create_rule(db, obj.model_dump()))


@router.put(
    '/code-rule/{rule_id}',
    dependencies=[Depends(RequestPermission('mes:trace:rule:config')), DependsRBAC],
)
async def update_code_rule(
    db: CurrentSessionTransaction,
    rule_id: Annotated[int, Path(ge=1)],
    obj: UpdateTraceCodeRuleParam,
) -> ResponseSchemaModel[TraceCodeRuleDetail]:
    return response_base.success(data=await trace_service.update_rule(db, rule_id, obj.model_dump()))


@router.post('/code-rule/preview', dependencies=[DependsJwtAuth])
async def preview_code_rule(
    db: CurrentSession, obj: TraceCodePreviewParam
) -> ResponseSchemaModel[dict[str, str]]:
    return response_base.success(data=await trace_service.preview_rule(db, obj))


@router.get('/material-rule/{material_id}', dependencies=[DependsJwtAuth])
async def get_material_rule(
    db: CurrentSession, material_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[MaterialTraceRuleDetail]:
    return response_base.success(data=await trace_service.get_material_rule(db, material_id))


@router.put(
    '/material-rule/{material_id}',
    dependencies=[Depends(RequestPermission('mes:trace:rule:config')), DependsRBAC],
)
async def update_material_rule(
    db: CurrentSessionTransaction,
    material_id: Annotated[int, Path(ge=1)],
    obj: MaterialTraceRuleParam,
) -> ResponseSchemaModel[MaterialTraceRuleDetail]:
    return response_base.success(data=await trace_service.update_material_rule(db, material_id, obj))


@router.get('/lot', dependencies=[DependsJwtAuth, DependsPagination])
async def list_lots(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[LotStatus | None, Query()] = None,
) -> ResponseSchemaModel[PageData[LotDetail]]:
    return response_base.success(data=await trace_service.list_lots(db, keyword, material_id, status))


@router.post(
    '/lot',
    dependencies=[Depends(RequestPermission('mes:trace:lot:config')), DependsRBAC],
)
async def create_lot(db: CurrentSessionTransaction, obj: CreateMaterialLotParam) -> ResponseSchemaModel[LotDetail]:
    return response_base.success(data=await trace_service.create_lot(db, obj))


@router.post(
    '/lot/merge',
    dependencies=[Depends(RequestPermission('mes:trace:lot:config')), DependsRBAC],
)
async def merge_lots(db: CurrentSessionTransaction, obj: LotMergeParam) -> ResponseSchemaModel[LotDetail]:
    return response_base.success(data=await trace_service.merge_lots(db, obj))


@router.get('/lot/{lot_id}', dependencies=[DependsJwtAuth])
async def get_lot(db: CurrentSession, lot_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[LotDetail]:
    return response_base.success(data=await trace_service.get_lot(db, lot_id))


@router.put(
    '/lot/{lot_id}/status',
    dependencies=[Depends(RequestPermission('mes:trace:lot:config')), DependsRBAC],
)
async def update_lot_status(
    db: CurrentSessionTransaction,
    lot_id: Annotated[int, Path(ge=1)],
    obj: LotStatusParam,
) -> ResponseSchemaModel[LotDetail]:
    return response_base.success(data=await trace_service.update_lot_status(db, lot_id, obj.status))


@router.post(
    '/lot/{lot_id}/split',
    dependencies=[Depends(RequestPermission('mes:trace:lot:config')), DependsRBAC],
)
async def split_lot(
    db: CurrentSessionTransaction,
    lot_id: Annotated[int, Path(ge=1)],
    obj: LotSplitParam,
) -> ResponseSchemaModel[list[LotDetail]]:
    return response_base.success(data=await trace_service.split_lot(db, lot_id, obj))


@router.get('/serial', dependencies=[DependsJwtAuth, DependsPagination])
async def list_serials(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    lot_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SerialStatus | None, Query()] = None,
) -> ResponseSchemaModel[PageData[MaterialSerialListItem]]:
    return response_base.success(data=await trace_service.list_serials(db, keyword, material_id, lot_id, status))


@router.post(
    '/serial/generate',
    dependencies=[Depends(RequestPermission('mes:trace:serial:generate')), DependsRBAC],
)
async def generate_serials(
    db: CurrentSessionTransaction, obj: GenerateMaterialSerialParam
) -> ResponseSchemaModel[MaterialSerialGenerateResult]:
    serials = await trace_service.generate_serials(db, obj)
    return response_base.success(data={'count': len(serials), 'serials': serials})


@router.get('/serial/{serial_id}', dependencies=[DependsJwtAuth])
async def get_serial(
    db: CurrentSession, serial_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[MaterialSerialDetail]:
    return response_base.success(data=await trace_service.get_serial(db, serial_id))


@router.put(
    '/serial/{serial_id}/status',
    dependencies=[Depends(RequestPermission('mes:trace:serial:generate')), DependsRBAC],
)
async def update_serial_status(
    db: CurrentSessionTransaction,
    serial_id: Annotated[int, Path(ge=1)],
    obj: SerialStatusParam,
) -> ResponseSchemaModel[MaterialSerialDetail]:
    return response_base.success(data=await trace_service.update_serial_status(db, serial_id, obj.status))


@router.post(
    '/relation',
    dependencies=[Depends(RequestPermission('mes:trace:relation:config')), DependsRBAC],
)
async def create_relation(
    db: CurrentSessionTransaction, obj: CreateTraceRelationParam
) -> ResponseSchemaModel[TraceRelationDetail]:
    return response_base.success(data=await trace_service.create_relation(db, obj))


@router.get('/forward', dependencies=[Depends(RequestPermission('mes:trace:query')), DependsRBAC])
async def forward_trace(
    db: CurrentSession,
    object_type: Annotated[TraceObjectType, Query(alias='type')],
    code: Annotated[str, Query(min_length=1, max_length=120)],
    max_depth: Annotated[int, Query(ge=1, le=30)] = 30,
) -> ResponseSchemaModel[TraceNode]:
    return response_base.success(data=await trace_service.trace(db, object_type, code, forward=True, max_depth=max_depth))


@router.get('/backward', dependencies=[Depends(RequestPermission('mes:trace:query')), DependsRBAC])
async def backward_trace(
    db: CurrentSession,
    object_type: Annotated[TraceObjectType, Query(alias='type')],
    code: Annotated[str, Query(min_length=1, max_length=120)],
    max_depth: Annotated[int, Query(ge=1, le=30)] = 30,
) -> ResponseSchemaModel[TraceNode]:
    return response_base.success(data=await trace_service.trace(db, object_type, code, forward=False, max_depth=max_depth))
