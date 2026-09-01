from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.scheduling.schema.workforce import (
    AccessCheckInput,
    AccessCheckResult,
    JobTypeDetail,
    JobTypeInput,
    PositionRuleDetail,
    PositionRuleInput,
    SkillLevelDetail,
    SkillLevelInput,
    WorkerAuthorizationDetail,
    WorkerAuthorizationInput,
    WorkerCertificateDetail,
    WorkerCertificateInput,
    WorkforceDashboard,
    WorkerRosterDetail,
    WorkerRosterInput,
    WorkerSkillDetail,
    WorkerSkillInput,
)
from backend.plugin.scheduling.service import workforce_service


router = APIRouter()
view = [DependsJwtAuth, Depends(RequestPermission('mes:workforce:view')), DependsRBAC]
manage = [Depends(RequestPermission('mes:workforce:manage')), DependsRBAC]


@router.get('/dashboard', dependencies=view)
async def dashboard(db: CurrentSession) -> ResponseSchemaModel[WorkforceDashboard]:
    return response_base.success(data=await workforce_service.dashboard(db))


@router.get('/job-types', dependencies=view)
async def job_types(db: CurrentSession) -> ResponseSchemaModel[list[JobTypeDetail]]:
    return response_base.success(data=await workforce_service.list_job_types(db))


@router.post('/job-types', dependencies=manage)
async def upsert_job_type(db: CurrentSessionTransaction, obj: JobTypeInput) -> ResponseSchemaModel[JobTypeDetail]:
    return response_base.success(data=await workforce_service.upsert_job_type(db, obj))


@router.get('/skill-levels', dependencies=view)
async def skill_levels(db: CurrentSession) -> ResponseSchemaModel[list[SkillLevelDetail]]:
    return response_base.success(data=await workforce_service.list_skill_levels(db))


@router.post('/skill-levels', dependencies=manage)
async def upsert_skill_level(db: CurrentSessionTransaction, obj: SkillLevelInput) -> ResponseSchemaModel[SkillLevelDetail]:
    return response_base.success(data=await workforce_service.upsert_skill_level(db, obj))


@router.get('/skills', dependencies=view)
async def skills(db: CurrentSession, user_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[WorkerSkillDetail]]:
    return response_base.success(data=await workforce_service.list_skills(db, user_id))


@router.post('/skills', dependencies=manage)
async def upsert_skill(db: CurrentSessionTransaction, obj: WorkerSkillInput) -> ResponseSchemaModel[WorkerSkillDetail]:
    return response_base.success(data=await workforce_service.upsert_skill(db, obj))


@router.get('/certificates', dependencies=view)
async def certificates(db: CurrentSession, user_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[WorkerCertificateDetail]]:
    return response_base.success(data=await workforce_service.list_certificates(db, user_id))


@router.post('/certificates', dependencies=manage)
async def upsert_certificate(db: CurrentSessionTransaction, obj: WorkerCertificateInput) -> ResponseSchemaModel[WorkerCertificateDetail]:
    return response_base.success(data=await workforce_service.upsert_certificate(db, obj))


@router.get('/rules', dependencies=view)
async def rules(db: CurrentSession) -> ResponseSchemaModel[list[PositionRuleDetail]]:
    return response_base.success(data=await workforce_service.list_rules(db))


@router.post('/rules', dependencies=manage)
async def upsert_rule(db: CurrentSessionTransaction, obj: PositionRuleInput) -> ResponseSchemaModel[PositionRuleDetail]:
    return response_base.success(data=await workforce_service.upsert_rule(db, obj))


@router.get('/authorizations', dependencies=view)
async def authorizations(db: CurrentSession, user_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[WorkerAuthorizationDetail]]:
    return response_base.success(data=await workforce_service.list_authorizations(db, user_id))


@router.post('/authorizations', dependencies=manage)
async def upsert_authorization(db: CurrentSessionTransaction, obj: WorkerAuthorizationInput) -> ResponseSchemaModel[WorkerAuthorizationDetail]:
    return response_base.success(data=await workforce_service.upsert_authorization(db, obj))


@router.get('/rosters', dependencies=view)
async def rosters(db: CurrentSession, work_date: Annotated[date | None, Query()] = None) -> ResponseSchemaModel[list[WorkerRosterDetail]]:
    return response_base.success(data=await workforce_service.list_rosters(db, work_date))


@router.post('/rosters', dependencies=manage)
async def upsert_roster(db: CurrentSessionTransaction, obj: WorkerRosterInput) -> ResponseSchemaModel[WorkerRosterDetail]:
    return response_base.success(data=await workforce_service.upsert_roster(db, obj))


@router.post('/access-check', dependencies=view)
async def access_check(db: CurrentSession, obj: AccessCheckInput) -> ResponseSchemaModel[AccessCheckResult]:
    return response_base.success(data=await workforce_service.check_access(db, obj.user_id, obj.operation_id, obj.work_center_id))
