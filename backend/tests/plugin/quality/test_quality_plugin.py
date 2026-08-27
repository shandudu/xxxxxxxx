from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.quality.api.v1.mes.quality import router
from backend.plugin.quality.enums import DispositionType, InspectionResult, InspectionType, ReworkStatus
from backend.plugin.quality.model import CustomerAfterSalesAudit, CustomerAfterSalesOrder, CustomerAfterSalesRepairTask, CustomerComplaint, CustomerReturn, CustomerReturnLine, NonconformanceDisposition, NonconformanceReport, QualityCapa, QualityCapaAction, QualityCapaVerification, QualityInspection, QualityInspectionItem, QualityInspectionResultLine, QualityInspectionStandard, QualityInspectionTemplate, QualityReworkOrder, QualitySamplingPlan
from backend.plugin.quality.schema.quality_standard import CreateQualitySamplingPlan
from backend.plugin.quality.schema.quality import CompleteInspection, CreateDisposition, CreateInspection
from backend.plugin.quality.service.quality_service import QualityService, incoming_sample_quantity


def test_quality_models_and_routes() -> None:
    assert QualityInspection.__tablename__ == 'mes_quality_inspection'
    assert NonconformanceReport.__tablename__ == 'mes_nonconformance_report'
    assert NonconformanceDisposition.__tablename__ == 'mes_nonconformance_disposition'
    assert QualityInspectionItem.__tablename__ == 'mes_quality_inspection_item'
    assert QualitySamplingPlan.__tablename__ == 'mes_quality_sampling_plan'
    assert QualityInspectionTemplate.__tablename__ == 'mes_quality_inspection_template'
    assert QualityInspectionStandard.__tablename__ == 'mes_quality_inspection_standard'
    assert QualityInspectionResultLine.__tablename__ == 'mes_quality_inspection_result'
    assert QualityReworkOrder.__tablename__ == 'mes_quality_rework_order'
    assert QualityCapa.__tablename__ == 'mes_quality_capa'
    assert QualityCapaAction.__tablename__ == 'mes_quality_capa_action'
    assert QualityCapaVerification.__tablename__ == 'mes_quality_capa_verification'
    assert CustomerComplaint.__tablename__ == 'erp_customer_complaint'
    assert CustomerReturn.__tablename__ == 'erp_customer_return'
    assert CustomerReturnLine.__tablename__ == 'erp_customer_return_line'
    assert CustomerAfterSalesOrder.__tablename__ == 'erp_customer_after_sales_order'
    assert CustomerAfterSalesRepairTask.__tablename__ == 'erp_customer_after_sales_repair_task'
    assert CustomerAfterSalesAudit.__tablename__ == 'erp_customer_after_sales_audit'
    assert len(router.routes) == 60
    assert '/supplier-scorecard' in {route.path for route in router.routes}
    assert '/dispositions/{disposition_id}/execute' in {route.path for route in router.routes}
    assert '/rework-orders' in {route.path for route in router.routes}
    assert '/rework-orders/{rework_id}/create-work-order' in {route.path for route in router.routes}
    assert '/capas' in {route.path for route in router.routes}
    assert '/capas/{capa_id}/verify' in {route.path for route in router.routes}
    assert '/customer-complaints' in {route.path for route in router.routes}
    assert '/customer-returns/{return_id}/inspect' in {route.path for route in router.routes}
    assert '/after-sales-orders/{order_id}/complete' in {route.path for route in router.routes}
    assert '/rework-orders/{rework_id}/complete' in {route.path for route in router.routes}
    assert '/inspection-items' in {route.path for route in router.routes}
    assert '/sampling-plans' in {route.path for route in router.routes}
    assert '/inspection-templates/{template_id}/standards' in {route.path for route in router.routes}
    assert '/inspections/{inspection_id}/results' in {route.path for route in router.routes}
    assert '/operation-dashboard' in {route.path for route in router.routes}
    assert '/sla-alerts/{alert_id}/escalate' in {route.path for route in router.routes}


def test_quality_schemas() -> None:
    inspection = CreateInspection(inspection_type=InspectionType.INCOMING, material_id=1, sample_quantity=Decimal('10'))
    assert inspection.sample_quantity == Decimal('10')
    disposition = CreateDisposition(ncr_id=1, disposition_type=DispositionType.REWORK, quantity=Decimal('2'))
    assert disposition.disposition_type == 'REWORK'
    assert ReworkStatus.AWAITING_RETEST == 'AWAITING_RETEST'


def test_pass_cannot_have_rejected_quantity() -> None:
    with pytest.raises(ValidationError):
        CompleteInspection(accepted_quantity=Decimal('9'), rejected_quantity=Decimal('1'), result=InspectionResult.PASS)


def test_sampling_acceptance_cannot_exceed_sample_size() -> None:
    with pytest.raises(ValidationError):
        CreateQualitySamplingPlan(plan_code='AQL-01', plan_name='AQL', sample_size=5, acceptance_number=6)


def test_incoming_sample_quantity_is_bounded_by_receipt_quantity() -> None:
    assert incoming_sample_quantity(Decimal('0.2'), 5) == Decimal('1')
    assert incoming_sample_quantity(Decimal('3.1'), 5) == Decimal('4')
    assert incoming_sample_quantity(Decimal('20'), 5) == Decimal('5')


def test_incoming_sample_quantity_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        incoming_sample_quantity(Decimal('0'), 5)


def test_quality_service_exposes_receipt_and_finished_lot_hooks() -> None:
    assert callable(QualityService.create_incoming_inspection)
    assert callable(QualityService.create_final_inspection)
