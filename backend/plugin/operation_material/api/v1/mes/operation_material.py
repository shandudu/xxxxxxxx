from typing import Annotated
from fastapi import APIRouter,Depends,Path,Response
from backend.common.response.response_schema import ResponseSchemaModel,response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession,CurrentSessionTransaction
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
from backend.plugin.operation_material.schema.operation_material import CreateOperationMaterialPlan,CreateOperationMaterialRequirement,PlanDetail,PlanValidation,RequirementDetail
from backend.plugin.operation_material.service import operation_material_service
router=APIRouter();view=[DependsJwtAuth,Depends(RequestPermission('mes:operation-material:view')),DependsRBAC]
@router.get('',dependencies=view)
async def list_plans(db:CurrentSession)->ResponseSchemaModel[list[PlanDetail]]:return response_base.success(data=await operation_material_service.list_plans(db))
@router.post('',dependencies=[Depends(RequestPermission('mes:operation-material:config')),DependsRBAC])
async def create_plan(db:CurrentSessionTransaction,obj:CreateOperationMaterialPlan)->ResponseSchemaModel[PlanDetail]:return response_base.success(data=await operation_material_service.create(db,obj))
@router.get('/{plan_id}',dependencies=view)
async def get_plan(db:CurrentSession,plan_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[PlanDetail]:return response_base.success(data=await operation_material_service.get(db,plan_id))
@router.get('/{plan_id}/requirements',dependencies=view)
async def requirements(db:CurrentSession,plan_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[list[RequirementDetail]]:return response_base.success(data=await operation_material_service.requirements(db,plan_id))
@router.post('/{plan_id}/requirements',dependencies=[Depends(RequestPermission('mes:operation-material:config')),DependsRBAC])
async def add_requirement(db:CurrentSessionTransaction,plan_id:Annotated[int,Path(ge=1)],obj:CreateOperationMaterialRequirement)->ResponseSchemaModel[RequirementDetail]:return response_base.success(data=await operation_material_service.add_requirement(db,plan_id,obj))
@router.put('/{plan_id}/requirements/{requirement_id}',dependencies=[Depends(RequestPermission('mes:operation-material:config')),DependsRBAC])
async def update_requirement(db:CurrentSessionTransaction,plan_id:Annotated[int,Path(ge=1)],requirement_id:Annotated[int,Path(ge=1)],obj:CreateOperationMaterialRequirement)->ResponseSchemaModel[RequirementDetail]:return response_base.success(data=await operation_material_service.update_requirement(db,plan_id,requirement_id,obj))
@router.delete('/{plan_id}/requirements/{requirement_id}',status_code=204,dependencies=[Depends(RequestPermission('mes:operation-material:config')),DependsRBAC])
async def delete_requirement(db:CurrentSessionTransaction,plan_id:Annotated[int,Path(ge=1)],requirement_id:Annotated[int,Path(ge=1)]) -> Response:await operation_material_service.delete_requirement(db,plan_id,requirement_id);return Response(status_code=204)
@router.post('/{plan_id}/validate',dependencies=[Depends(RequestPermission('mes:operation-material:config')),DependsRBAC])
async def validate_plan(db:CurrentSession,plan_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[PlanValidation]:return response_base.success(data=await operation_material_service.validate(db,plan_id))
@router.post('/{plan_id}/activate',dependencies=[Depends(RequestPermission('mes:operation-material:status')),DependsRBAC])
async def activate(db:CurrentSessionTransaction,plan_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[PlanDetail]:return response_base.success(data=await operation_material_service.status(db,plan_id,OperationMaterialPlanStatus.ACTIVE))
@router.post('/{plan_id}/deactivate',dependencies=[Depends(RequestPermission('mes:operation-material:status')),DependsRBAC])
async def deactivate(db:CurrentSessionTransaction,plan_id:Annotated[int,Path(ge=1)])->ResponseSchemaModel[PlanDetail]:return response_base.success(data=await operation_material_service.status(db,plan_id,OperationMaterialPlanStatus.INACTIVE))
