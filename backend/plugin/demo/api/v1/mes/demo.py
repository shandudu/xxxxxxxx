from fastapi import APIRouter, Depends

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.demo.schema.demo import ManufacturingDemoRunDetail, ManufacturingDemoStatus, ManufacturingDemoVerifyResult
from backend.plugin.demo.service import demo_service


router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:demo:view')), DependsRBAC]


@router.post('/manufacturing-happy-path/run', dependencies=[Depends(RequestPermission('mes:demo:run')), DependsRBAC])
async def run(db: CurrentSessionTransaction) -> ResponseSchemaModel[ManufacturingDemoRunDetail]:
    return response_base.success(data=await demo_service.run(db))


@router.get('/manufacturing-happy-path/status', dependencies=view_dependencies)
async def status(db: CurrentSession) -> ResponseSchemaModel[ManufacturingDemoStatus]:
    return response_base.success(data=await demo_service.status(db))


@router.post('/manufacturing-happy-path/verify', dependencies=view_dependencies)
async def verify(db: CurrentSession) -> ResponseSchemaModel[ManufacturingDemoVerifyResult]:
    return response_base.success(data=await demo_service.verify(db))


@router.post('/sales-order-driven-happy-path/run', dependencies=[Depends(RequestPermission('mes:demo:run')), DependsRBAC])
async def run_sales_order_driven(db: CurrentSessionTransaction) -> ResponseSchemaModel[ManufacturingDemoRunDetail]:
    return response_base.success(data=await demo_service.run_sales_order_driven(db))


@router.get('/sales-order-driven-happy-path/status', dependencies=view_dependencies)
async def sales_order_driven_status(db: CurrentSession) -> ResponseSchemaModel[ManufacturingDemoStatus]:
    return response_base.success(data=await demo_service.sales_order_driven_status(db))


@router.post('/sales-order-driven-happy-path/verify', dependencies=view_dependencies)
async def verify_sales_order_driven(db: CurrentSession) -> ResponseSchemaModel[ManufacturingDemoVerifyResult]:
    return response_base.success(data=await demo_service.verify_sales_order_driven(db))
