from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import Field

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.schema import SchemaBase
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.quality.schema.quality import AfterSalesAuditDetail, AfterSalesOrderDetail, AfterSalesRepairTaskDetail, CompleteAfterSalesRepairTask, CapaActionDetail, CapaDetail, CapaVerificationDetail, CompleteCustomerReturnInspection, CompleteInspection, CreateAfterSalesOrder, CreateCapa, CreateCapaAction, CreateCustomerComplaint, CreateCustomerReturn, CreateDisposition, CreateInspection, CreateNcr, CustomerComplaintDetail, CustomerReturnDetail, DispositionDetail, InspectionDetail, NcrDetail, OperationDashboardSummary, ReworkOrderDetail, ResolveCustomerReturn, SetCapaActionStatus, SlaRuleDetail, SupplierQualityScorecard, UpdateCapa, VerifyCapa, WorkItemAlertDetail, EscalateWorkItemAlert
from backend.plugin.quality.schema.quality_standard import (
    CreateQualityInspectionItem,
    CreateQualityInspectionStandard,
    CreateQualityInspectionTemplate,
    CreateQualitySamplingPlan,
    QualityInspectionItemDetail,
    QualityInspectionResultLineDetail,
    QualityInspectionStandardDetail,
    QualityInspectionTemplateDetail,
    QualitySamplingPlanDetail,
    SetQualityConfigStatus,
    SubmitQualityResults,
)
from backend.plugin.quality.schema.sqm import (
    IssueSupplierCorrectiveAction,
    RespondSupplierCorrectiveAction,
    SupplierCorrectiveActionDetail,
    SupplierQualityAssessmentDetail,
    SupplierQualityDashboard,
    SupplierQualityPolicyDetail,
    SupplierQualityPolicyUpsert,
    VerifySupplierCorrectiveAction,
)
from backend.plugin.quality.enums import InspectionTemplateStatus
from backend.plugin.quality.service import quality_service, quality_standard_service, sqm_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('mes:quality:view')), DependsRBAC]


@router.get('/operation-dashboard', dependencies=view_dependencies)
async def get_operation_dashboard(db: CurrentSession) -> ResponseSchemaModel[OperationDashboardSummary]:
    return response_base.success(data=await quality_service.operation_dashboard(db))


@router.get('/sla-rules', dependencies=view_dependencies)
async def list_sla_rules(db: CurrentSession) -> ResponseSchemaModel[list[SlaRuleDetail]]:
    return response_base.success(data=await quality_service.list_sla_rules(db))


@router.get('/sla-alerts', dependencies=view_dependencies)
async def list_sla_alerts(db: CurrentSession, status: Annotated[str | None, Query()] = None, owner_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[WorkItemAlertDetail]]:
    return response_base.success(data=await quality_service.list_sla_alerts(db, status, owner_id))


@router.post('/sla-alerts/{alert_id}/acknowledge', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def acknowledge_sla_alert(db: CurrentSessionTransaction, alert_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkItemAlertDetail]:
    return response_base.success(data=await quality_service.acknowledge_sla_alert(db, alert_id))


@router.post('/sla-alerts/{alert_id}/escalate', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def escalate_sla_alert(db: CurrentSessionTransaction, alert_id: Annotated[int, Path(ge=1)], obj: EscalateWorkItemAlert) -> ResponseSchemaModel[WorkItemAlertDetail]:
    return response_base.success(data=await quality_service.escalate_sla_alert(db, alert_id, obj.level))


@router.post('/sla-alerts/{alert_id}/close', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def close_sla_alert(db: CurrentSessionTransaction, alert_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[WorkItemAlertDetail]:
    return response_base.success(data=await quality_service.close_sla_alert(db, alert_id))


@router.get('/supplier-scorecard', dependencies=view_dependencies)
async def get_supplier_scorecard(db: CurrentSession) -> ResponseSchemaModel[list[SupplierQualityScorecard]]:
    return response_base.success(data=await quality_service.supplier_scorecard(db))


@router.get('/sqm/dashboard', dependencies=[Depends(RequestPermission('mes:quality:sqm:view')), DependsRBAC])
async def get_sqm_dashboard(db: CurrentSession) -> ResponseSchemaModel[SupplierQualityDashboard]:
    return response_base.success(data=await sqm_service.dashboard(db))


@router.get('/sqm/scars', dependencies=[Depends(RequestPermission('mes:quality:sqm:view')), DependsRBAC])
async def list_supplier_scars(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[str | None, Query(max_length=30)] = None,
) -> ResponseSchemaModel[list[SupplierCorrectiveActionDetail]]:
    return response_base.success(data=await sqm_service.list_scars(db, supplier_id, status))


@router.post('/sqm/scars/{scar_id}/issue', dependencies=[Depends(RequestPermission('mes:quality:sqm:scar')), DependsRBAC])
async def issue_supplier_scar(
    db: CurrentSessionTransaction,
    scar_id: Annotated[int, Path(ge=1)],
    obj: IssueSupplierCorrectiveAction,
) -> ResponseSchemaModel[SupplierCorrectiveActionDetail]:
    return response_base.success(data=await sqm_service.issue_scar(db, scar_id, obj))


@router.post('/sqm/scars/{scar_id}/respond', dependencies=[Depends(RequestPermission('mes:quality:sqm:scar')), DependsRBAC])
async def respond_supplier_scar(
    db: CurrentSessionTransaction,
    scar_id: Annotated[int, Path(ge=1)],
    obj: RespondSupplierCorrectiveAction,
) -> ResponseSchemaModel[SupplierCorrectiveActionDetail]:
    return response_base.success(data=await sqm_service.respond_scar(db, scar_id, obj))


@router.post('/sqm/scars/{scar_id}/reinspect', dependencies=[Depends(RequestPermission('mes:quality:sqm:verify')), DependsRBAC])
async def reinspect_supplier_scar(
    db: CurrentSessionTransaction,
    scar_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[SupplierCorrectiveActionDetail]:
    return response_base.success(data=await sqm_service.create_reinspection(db, scar_id))


@router.post('/sqm/scars/{scar_id}/verify', dependencies=[Depends(RequestPermission('mes:quality:sqm:verify')), DependsRBAC])
async def verify_supplier_scar(
    db: CurrentSessionTransaction,
    scar_id: Annotated[int, Path(ge=1)],
    obj: VerifySupplierCorrectiveAction,
) -> ResponseSchemaModel[SupplierCorrectiveActionDetail]:
    return response_base.success(data=await sqm_service.verify_scar(db, scar_id, obj))


@router.get('/sqm/policies', dependencies=[Depends(RequestPermission('mes:quality:sqm:view')), DependsRBAC])
async def list_supplier_quality_policies(
    db: CurrentSession,
) -> ResponseSchemaModel[list[SupplierQualityPolicyDetail]]:
    return response_base.success(data=await sqm_service.list_policies(db))


@router.put('/sqm/policies/{supplier_id}', dependencies=[Depends(RequestPermission('mes:quality:sqm:policy')), DependsRBAC])
async def upsert_supplier_quality_policy(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierQualityPolicyUpsert,
) -> ResponseSchemaModel[SupplierQualityPolicyDetail]:
    return response_base.success(data=await sqm_service.upsert_policy(db, supplier_id, obj))


@router.get('/sqm/assessments', dependencies=[Depends(RequestPermission('mes:quality:sqm:view')), DependsRBAC])
async def list_supplier_quality_assessments(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> ResponseSchemaModel[list[SupplierQualityAssessmentDetail]]:
    return response_base.success(data=await sqm_service.list_assessments(db, supplier_id, limit))


@router.post('/sqm/assessments/{supplier_id}/recalculate', dependencies=[Depends(RequestPermission('mes:quality:sqm:policy')), DependsRBAC])
async def assess_supplier_quality(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
) -> ResponseSchemaModel[SupplierQualityAssessmentDetail]:
    return response_base.success(data=await sqm_service.assess_supplier(db, supplier_id))


@router.post('/sqm/assessments/recalculate-all', dependencies=[Depends(RequestPermission('mes:quality:sqm:policy')), DependsRBAC])
async def assess_all_supplier_quality(
    db: CurrentSessionTransaction,
) -> ResponseSchemaModel[list[SupplierQualityAssessmentDetail]]:
    return response_base.success(data=await sqm_service.assess_all(db))


class CloseNcrParam(SchemaBase):
    root_cause: str | None = Field(default=None, max_length=4000)


@router.get('/inspections', dependencies=view_dependencies)
async def list_inspections(db: CurrentSession, inspection_type: Annotated[str | None, Query()] = None, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[InspectionDetail]]:
    return response_base.success(data=await quality_service.list_inspections(db, inspection_type, status))


@router.post('/inspections', dependencies=[Depends(RequestPermission('mes:quality:inspection')), DependsRBAC])
async def create_inspection(db: CurrentSessionTransaction, obj: CreateInspection) -> ResponseSchemaModel[InspectionDetail]:
    return response_base.success(data=await quality_service.create_inspection(db, obj))


@router.post('/inspections/{inspection_id}/complete', dependencies=[Depends(RequestPermission('mes:quality:inspection')), DependsRBAC])
async def complete_inspection(db: CurrentSessionTransaction, inspection_id: Annotated[int, Path(ge=1)], obj: CompleteInspection) -> ResponseSchemaModel[InspectionDetail]:
    return response_base.success(data=await quality_service.complete_inspection(db, inspection_id, obj))


@router.get('/ncrs', dependencies=view_dependencies)
async def list_ncrs(db: CurrentSession, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[NcrDetail]]:
    return response_base.success(data=await quality_service.list_ncrs(db, status))


@router.post('/ncrs', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def create_ncr(db: CurrentSessionTransaction, obj: CreateNcr) -> ResponseSchemaModel[NcrDetail]:
    return response_base.success(data=await quality_service.create_ncr(db, obj))


@router.get('/ncrs/{ncr_id}/dispositions', dependencies=view_dependencies)
async def list_dispositions(db: CurrentSession, ncr_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[DispositionDetail]]:
    return response_base.success(data=await quality_service.list_dispositions(db, ncr_id))


@router.post('/dispositions', dependencies=[Depends(RequestPermission('mes:quality:mrb')), DependsRBAC])
async def create_disposition(db: CurrentSessionTransaction, obj: CreateDisposition) -> ResponseSchemaModel[DispositionDetail]:
    return response_base.success(data=await quality_service.create_disposition(db, obj))


@router.post('/dispositions/{disposition_id}/execute', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def execute_disposition(db: CurrentSessionTransaction, disposition_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[DispositionDetail]:
    return response_base.success(data=await quality_service.execute_disposition(db, disposition_id))


@router.get('/rework-orders', dependencies=view_dependencies)
async def list_rework_orders(db: CurrentSession, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[ReworkOrderDetail]]:
    return response_base.success(data=await quality_service.list_rework_orders(db, status))


@router.post('/rework-orders/{rework_id}/create-work-order', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def create_rework_work_order(db: CurrentSessionTransaction, rework_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ReworkOrderDetail]:
    return response_base.success(data=await quality_service.create_rework_work_order(db, rework_id))


@router.post('/rework-orders/{rework_id}/start', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def start_rework(db: CurrentSessionTransaction, rework_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ReworkOrderDetail]:
    return response_base.success(data=await quality_service.start_rework(db, rework_id))


@router.post('/rework-orders/{rework_id}/complete', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def complete_rework(db: CurrentSessionTransaction, rework_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ReworkOrderDetail]:
    return response_base.success(data=await quality_service.complete_rework(db, rework_id))


@router.post('/ncrs/{ncr_id}/close', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def close_ncr(db: CurrentSessionTransaction, ncr_id: Annotated[int, Path(ge=1)], obj: CloseNcrParam) -> ResponseSchemaModel[NcrDetail]:
    return response_base.success(data=await quality_service.close_ncr(db, ncr_id, obj.root_cause))


@router.get('/capas', dependencies=view_dependencies)
async def list_capas(db: CurrentSession, status: Annotated[str | None, Query()] = None, ncr_id: Annotated[int | None, Query(ge=1)] = None) -> ResponseSchemaModel[list[CapaDetail]]:
    return response_base.success(data=await quality_service.list_capas(db, status, ncr_id))


@router.post('/capas', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def create_capa(db: CurrentSessionTransaction, obj: CreateCapa) -> ResponseSchemaModel[CapaDetail]:
    return response_base.success(data=await quality_service.create_capa(db, obj))


@router.put('/capas/{capa_id}', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def update_capa(db: CurrentSessionTransaction, capa_id: Annotated[int, Path(ge=1)], obj: UpdateCapa) -> ResponseSchemaModel[CapaDetail]:
    return response_base.success(data=await quality_service.update_capa(db, capa_id, obj))


@router.get('/capas/{capa_id}/actions', dependencies=view_dependencies)
async def list_capa_actions(db: CurrentSession, capa_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[CapaActionDetail]]:
    return response_base.success(data=await quality_service.list_capa_actions(db, capa_id))


@router.post('/capas/{capa_id}/actions', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def create_capa_action(db: CurrentSessionTransaction, capa_id: Annotated[int, Path(ge=1)], obj: CreateCapaAction) -> ResponseSchemaModel[CapaActionDetail]:
    return response_base.success(data=await quality_service.create_capa_action(db, capa_id, obj))


@router.post('/capas/{capa_id}/actions/{action_id}/status', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def set_capa_action_status(db: CurrentSessionTransaction, capa_id: Annotated[int, Path(ge=1)], action_id: Annotated[int, Path(ge=1)], obj: SetCapaActionStatus) -> ResponseSchemaModel[CapaActionDetail]:
    return response_base.success(data=await quality_service.set_capa_action_status(db, capa_id, action_id, obj))


@router.get('/capas/{capa_id}/verifications', dependencies=view_dependencies)
async def list_capa_verifications(db: CurrentSession, capa_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[CapaVerificationDetail]]:
    return response_base.success(data=await quality_service.list_capa_verifications(db, capa_id))


@router.post('/capas/{capa_id}/verify', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def verify_capa(db: CurrentSessionTransaction, capa_id: Annotated[int, Path(ge=1)], obj: VerifyCapa) -> ResponseSchemaModel[CapaVerificationDetail]:
    return response_base.success(data=await quality_service.verify_capa(db, capa_id, obj))


@router.post('/capas/{capa_id}/close', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def close_capa(db: CurrentSessionTransaction, capa_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CapaDetail]:
    return response_base.success(data=await quality_service.close_capa(db, capa_id))


@router.get('/customer-complaints', dependencies=view_dependencies)
async def list_customer_complaints(db: CurrentSession, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[CustomerComplaintDetail]]:
    return response_base.success(data=await quality_service.list_customer_complaints(db, status))


@router.post('/customer-complaints', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def create_customer_complaint(db: CurrentSessionTransaction, obj: CreateCustomerComplaint) -> ResponseSchemaModel[CustomerComplaintDetail]:
    return response_base.success(data=await quality_service.create_customer_complaint(db, obj))


@router.get('/customer-returns', dependencies=view_dependencies)
async def list_customer_returns(db: CurrentSession, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[CustomerReturnDetail]]:
    return response_base.success(data=await quality_service.list_customer_returns(db, status))


@router.post('/customer-returns', dependencies=[Depends(RequestPermission('mes:quality:ncr')), DependsRBAC])
async def create_customer_return(db: CurrentSessionTransaction, obj: CreateCustomerReturn) -> ResponseSchemaModel[CustomerReturnDetail]:
    return response_base.success(data=await quality_service.create_customer_return(db, obj))


@router.post('/customer-returns/{return_id}/receive', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def receive_customer_return(db: CurrentSessionTransaction, return_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CustomerReturnDetail]:
    return response_base.success(data=await quality_service.receive_customer_return(db, return_id))


@router.post('/customer-returns/{return_id}/inspect', dependencies=[Depends(RequestPermission('mes:quality:inspection')), DependsRBAC])
async def inspect_customer_return(db: CurrentSessionTransaction, return_id: Annotated[int, Path(ge=1)], obj: CompleteCustomerReturnInspection) -> ResponseSchemaModel[CustomerReturnDetail]:
    return response_base.success(data=await quality_service.inspect_customer_return(db, return_id, obj))


@router.post('/customer-returns/{return_id}/resolve', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def resolve_customer_return(db: CurrentSessionTransaction, return_id: Annotated[int, Path(ge=1)], obj: ResolveCustomerReturn) -> ResponseSchemaModel[CustomerReturnDetail]:
    return response_base.success(data=await quality_service.resolve_customer_return(db, return_id, obj))


@router.post('/customer-returns/{return_id}/close', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def close_customer_return(db: CurrentSessionTransaction, return_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CustomerReturnDetail]:
    return response_base.success(data=await quality_service.close_customer_return(db, return_id))


@router.get('/after-sales-orders', dependencies=view_dependencies)
async def list_after_sales_orders(db: CurrentSession, status: Annotated[str | None, Query()] = None) -> ResponseSchemaModel[list[AfterSalesOrderDetail]]:
    return response_base.success(data=await quality_service.list_after_sales_orders(db, status))


@router.post('/customer-returns/{return_id}/after-sales-orders', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def create_after_sales_order(db: CurrentSessionTransaction, return_id: Annotated[int, Path(ge=1)], obj: CreateAfterSalesOrder) -> ResponseSchemaModel[AfterSalesOrderDetail]:
    return response_base.success(data=await quality_service.create_after_sales_order(db, return_id, obj))


@router.post('/after-sales-orders/{order_id}/approve', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def approve_after_sales_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AfterSalesOrderDetail]:
    return response_base.success(data=await quality_service.approve_after_sales_order(db, order_id))


@router.post('/after-sales-orders/{order_id}/start', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def start_after_sales_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AfterSalesOrderDetail]:
    return response_base.success(data=await quality_service.start_after_sales_order(db, order_id))


@router.post('/after-sales-orders/{order_id}/complete', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def complete_after_sales_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AfterSalesOrderDetail]:
    return response_base.success(data=await quality_service.complete_after_sales_order(db, order_id))


@router.post('/after-sales-orders/{order_id}/cancel', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def cancel_after_sales_order(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AfterSalesOrderDetail]:
    return response_base.success(data=await quality_service.cancel_after_sales_order(db, order_id))


@router.get('/after-sales-orders/{order_id}/audits', dependencies=view_dependencies)
async def list_after_sales_audits(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[AfterSalesAuditDetail]]:
    return response_base.success(data=await quality_service.list_after_sales_audits(db, order_id))


@router.get('/after-sales-orders/{order_id}/repair-task', dependencies=view_dependencies)
async def get_after_sales_repair_task(db: CurrentSession, order_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[AfterSalesRepairTaskDetail]:
    return response_base.success(data=await quality_service.get_after_sales_repair_task(db, order_id))


@router.post('/after-sales-orders/{order_id}/repair-task/complete', dependencies=[Depends(RequestPermission('mes:quality:mrb:execute')), DependsRBAC])
async def complete_after_sales_repair_task(db: CurrentSessionTransaction, order_id: Annotated[int, Path(ge=1)], obj: CompleteAfterSalesRepairTask) -> ResponseSchemaModel[AfterSalesRepairTaskDetail]:
    return response_base.success(data=await quality_service.complete_after_sales_repair_task(db, order_id, obj))


config_dependencies = [Depends(RequestPermission('mes:quality:config')), DependsRBAC]


@router.get('/inspection-items', dependencies=view_dependencies)
async def list_inspection_items(db: CurrentSession) -> ResponseSchemaModel[list[QualityInspectionItemDetail]]:
    return response_base.success(data=await quality_standard_service.list_items(db))


@router.post('/inspection-items', dependencies=config_dependencies)
async def create_inspection_item(db: CurrentSessionTransaction, obj: CreateQualityInspectionItem) -> ResponseSchemaModel[QualityInspectionItemDetail]:
    return response_base.success(data=await quality_standard_service.create_item(db, obj))


@router.put('/inspection-items/{item_id}/status', dependencies=config_dependencies)
async def set_inspection_item_status(db: CurrentSessionTransaction, item_id: Annotated[int, Path(ge=1)], obj: SetQualityConfigStatus) -> ResponseSchemaModel[QualityInspectionItemDetail]:
    return response_base.success(data=await quality_standard_service.set_item_status(db, item_id, obj.status))


@router.get('/sampling-plans', dependencies=view_dependencies)
async def list_sampling_plans(db: CurrentSession) -> ResponseSchemaModel[list[QualitySamplingPlanDetail]]:
    return response_base.success(data=await quality_standard_service.list_sampling_plans(db))


@router.post('/sampling-plans', dependencies=config_dependencies)
async def create_sampling_plan(db: CurrentSessionTransaction, obj: CreateQualitySamplingPlan) -> ResponseSchemaModel[QualitySamplingPlanDetail]:
    return response_base.success(data=await quality_standard_service.create_sampling_plan(db, obj))


@router.put('/sampling-plans/{plan_id}/status', dependencies=config_dependencies)
async def set_sampling_plan_status(db: CurrentSessionTransaction, plan_id: Annotated[int, Path(ge=1)], obj: SetQualityConfigStatus) -> ResponseSchemaModel[QualitySamplingPlanDetail]:
    return response_base.success(data=await quality_standard_service.set_sampling_plan_status(db, plan_id, obj.status))


@router.get('/inspection-templates', dependencies=view_dependencies)
async def list_inspection_templates(db: CurrentSession) -> ResponseSchemaModel[list[QualityInspectionTemplateDetail]]:
    return response_base.success(data=await quality_standard_service.list_templates(db))


@router.post('/inspection-templates', dependencies=config_dependencies)
async def create_inspection_template(db: CurrentSessionTransaction, obj: CreateQualityInspectionTemplate) -> ResponseSchemaModel[QualityInspectionTemplateDetail]:
    return response_base.success(data=await quality_standard_service.create_template(db, obj))


@router.get('/inspection-templates/{template_id}/standards', dependencies=view_dependencies)
async def list_inspection_standards(db: CurrentSession, template_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[QualityInspectionStandardDetail]]:
    return response_base.success(data=await quality_standard_service.standards(db, template_id))


@router.post('/inspection-templates/{template_id}/standards', dependencies=config_dependencies)
async def add_inspection_standard(db: CurrentSessionTransaction, template_id: Annotated[int, Path(ge=1)], obj: CreateQualityInspectionStandard) -> ResponseSchemaModel[QualityInspectionStandardDetail]:
    return response_base.success(data=await quality_standard_service.add_standard(db, template_id, obj))


@router.post('/inspection-templates/{template_id}/activate', dependencies=config_dependencies)
async def activate_inspection_template(db: CurrentSessionTransaction, template_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[QualityInspectionTemplateDetail]:
    return response_base.success(data=await quality_standard_service.set_template_status(db, template_id, InspectionTemplateStatus.ACTIVE))


@router.post('/inspection-templates/{template_id}/deactivate', dependencies=config_dependencies)
async def deactivate_inspection_template(db: CurrentSessionTransaction, template_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[QualityInspectionTemplateDetail]:
    return response_base.success(data=await quality_standard_service.set_template_status(db, template_id, InspectionTemplateStatus.INACTIVE))


@router.get('/inspections/{inspection_id}/results', dependencies=view_dependencies)
async def list_inspection_results(db: CurrentSession, inspection_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[QualityInspectionResultLineDetail]]:
    return response_base.success(data=await quality_standard_service.results(db, inspection_id))


@router.post('/inspections/{inspection_id}/results', dependencies=[Depends(RequestPermission('mes:quality:inspection')), DependsRBAC])
async def submit_inspection_results(db: CurrentSessionTransaction, inspection_id: Annotated[int, Path(ge=1)], obj: SubmitQualityResults) -> ResponseSchemaModel[list[QualityInspectionResultLineDetail]]:
    return response_base.success(data=await quality_standard_service.submit_results(db, inspection_id, obj))
