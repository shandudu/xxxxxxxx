from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.quality.enums import AfterSalesAuditAction, AfterSalesExecutionStatus, AfterSalesRepairTaskStatus, CapaActionStatus, CapaActionType, CapaStatus, CapaVerificationResult, CustomerComplaintStatus, CustomerReturnResolution, CustomerReturnStatus, DispositionStatus, DispositionType, InspectionResult, InspectionStatus, InspectionType, NcrStatus, ReworkStatus, SlaAlertStatus, SlaEntityType


class CreateInspection(SchemaBase):
    inspection_no: str | None = Field(default=None, max_length=100)
    inspection_type: InspectionType
    material_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    parent_inspection_id: int | None = Field(default=None, ge=1)
    source_type: str | None = Field(default=None, max_length=50)
    source_id: int | None = Field(default=None, ge=1)
    source_no: str | None = Field(default=None, max_length=100)
    sample_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class CompleteInspection(SchemaBase):
    accepted_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    rejected_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    result: InspectionResult
    conclusion: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_result(self):
        if self.result == InspectionResult.PASS and self.rejected_quantity > 0:
            raise ValueError('PASS inspection cannot contain rejected quantity')
        if self.result == InspectionResult.FAIL and self.rejected_quantity <= 0:
            raise ValueError('FAIL inspection requires rejected quantity')
        return self


class InspectionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inspection_no: str
    inspection_type: InspectionType
    material_id: int
    lot_id: int | None
    parent_inspection_id: int | None
    source_type: str | None
    source_id: int | None
    source_no: str | None
    sample_quantity: Decimal
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    status: InspectionStatus
    result: InspectionResult | None
    conclusion: str | None
    inspected_at: datetime | None
    created_time: datetime


class CreateNcr(SchemaBase):
    ncr_no: str | None = Field(default=None, max_length=100)
    inspection_id: int = Field(ge=1)
    nonconforming_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    defect_description: str = Field(min_length=1, max_length=4000)
    severity: str = Field(default='MAJOR', max_length=20)


class NcrDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ncr_no: str
    inspection_id: int
    material_id: int
    lot_id: int | None
    nonconforming_quantity: Decimal
    defect_description: str
    severity: str
    status: NcrStatus
    root_cause: str | None
    closed_at: datetime | None
    sla_due_at: datetime | None
    sla_owner_id: int | None
    created_time: datetime


class CreateDisposition(SchemaBase):
    disposition_no: str | None = Field(default=None, max_length=100)
    ncr_id: int = Field(ge=1)
    disposition_type: DispositionType
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    warehouse_id: int | None = Field(default=None, ge=1)
    location_id: int | None = Field(default=None, ge=1)
    decision_reason: str | None = Field(default=None, max_length=2000)


class DispositionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    disposition_no: str
    ncr_id: int
    disposition_type: DispositionType
    quantity: Decimal
    status: DispositionStatus
    warehouse_id: int | None
    location_id: int | None
    stock_transaction_id: int | None
    reinspection_id: int | None
    rework_order_id: int | None
    decision_reason: str | None
    executed_at: datetime | None
    created_time: datetime


class ReworkOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rework_no: str
    ncr_id: int
    material_id: int
    lot_id: int
    quantity: Decimal
    production_work_order_id: int | None = None
    status: ReworkStatus
    reinspection_id: int | None
    started_at: datetime | None
    completed_at: datetime | None
    released_at: datetime | None
    remark: str | None
    created_time: datetime


class SupplierQualityScorecard(SchemaBase):
    supplier_id: int
    supplier_code: str
    supplier_name: str
    inspection_count: int
    passed_count: int
    failed_count: int
    rejected_quantity: Decimal
    pass_rate: Decimal


class CreateCapa(SchemaBase):
    capa_no: str | None = Field(default=None, max_length=100)
    ncr_id: int = Field(ge=1)
    d1_team_summary: str | None = Field(default=None, max_length=4000)
    d2_problem_description: str | None = Field(default=None, max_length=4000)
    d3_containment_summary: str | None = Field(default=None, max_length=4000)
    d4_root_cause: str | None = Field(default=None, max_length=4000)
    d5_corrective_plan: str | None = Field(default=None, max_length=4000)
    d6_implementation_summary: str | None = Field(default=None, max_length=4000)
    d7_prevention_summary: str | None = Field(default=None, max_length=4000)
    d8_closure_summary: str | None = Field(default=None, max_length=4000)
    owner_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None


class UpdateCapa(SchemaBase):
    d1_team_summary: str | None = Field(default=None, max_length=4000)
    d2_problem_description: str | None = Field(default=None, max_length=4000)
    d3_containment_summary: str | None = Field(default=None, max_length=4000)
    d4_root_cause: str | None = Field(default=None, max_length=4000)
    d5_corrective_plan: str | None = Field(default=None, max_length=4000)
    d6_implementation_summary: str | None = Field(default=None, max_length=4000)
    d7_prevention_summary: str | None = Field(default=None, max_length=4000)
    d8_closure_summary: str | None = Field(default=None, max_length=4000)
    owner_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None


class CapaActionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action_no: str
    capa_id: int
    action_type: CapaActionType
    description: str
    owner_id: int | None
    due_at: datetime | None
    status: CapaActionStatus
    evidence: str | None
    completed_at: datetime | None
    verified_at: datetime | None
    created_time: datetime


class CreateCapaAction(SchemaBase):
    action_type: CapaActionType
    description: str = Field(min_length=1, max_length=4000)
    owner_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None


class SetCapaActionStatus(SchemaBase):
    status: CapaActionStatus
    evidence: str | None = Field(default=None, max_length=4000)


class CapaVerificationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    capa_id: int
    result: CapaVerificationResult
    notes: str | None
    verified_by: int | None
    verified_at: datetime


class VerifyCapa(SchemaBase):
    result: CapaVerificationResult
    notes: str | None = Field(default=None, max_length=4000)


class CapaDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    capa_no: str
    ncr_id: int
    status: CapaStatus
    d1_team_summary: str | None
    d2_problem_description: str | None
    d3_containment_summary: str | None
    d4_root_cause: str | None
    d5_corrective_plan: str | None
    d6_implementation_summary: str | None
    d7_prevention_summary: str | None
    d8_closure_summary: str | None
    owner_id: int | None
    due_at: datetime | None
    closed_at: datetime | None
    created_time: datetime


class CreateCustomerComplaint(SchemaBase):
    complaint_no: str | None = Field(default=None, max_length=100)
    customer_id: int = Field(ge=1)
    sales_order_id: int | None = Field(default=None, ge=1)
    shipment_id: int | None = Field(default=None, ge=1)
    material_id: int | None = Field(default=None, ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)


class CustomerComplaintDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    complaint_no: str
    customer_id: int
    customer_code_snapshot: str
    customer_name_snapshot: str
    sales_order_id: int | None
    shipment_id: int | None
    material_id: int | None
    lot_id: int | None
    quantity: Decimal | None
    title: str
    description: str
    status: CustomerComplaintStatus
    rma_id: int | None
    ncr_id: int | None
    capa_id: int | None
    resolution_type: CustomerReturnResolution | None
    resolution_notes: str | None
    closed_at: datetime | None
    sla_due_at: datetime | None
    sla_owner_id: int | None
    created_time: datetime


class CreateCustomerReturnLine(SchemaBase):
    shipment_line_id: int | None = Field(default=None, ge=1)
    material_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class CreateCustomerReturn(SchemaBase):
    return_no: str | None = Field(default=None, max_length=100)
    complaint_id: int = Field(ge=1)
    shipment_id: int | None = Field(default=None, ge=1)
    lines: list[CreateCustomerReturnLine] = Field(min_length=1, max_length=500)


class CustomerReturnLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    line_no: int
    shipment_line_id: int | None
    material_id: int
    lot_id: int | None
    warehouse_id: int
    location_id: int
    quantity: Decimal
    stock_transaction_id: int | None
    inspection_id: int | None


class CustomerReturnDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_no: str
    complaint_id: int
    customer_id: int
    shipment_id: int | None
    status: CustomerReturnStatus
    ncr_id: int | None
    resolution_type: CustomerReturnResolution | None
    resolution_notes: str | None
    received_at: datetime | None
    inspected_at: datetime | None
    closed_at: datetime | None
    sla_due_at: datetime | None
    sla_owner_id: int | None
    created_time: datetime
    lines: list[CustomerReturnLineDetail] = Field(default_factory=list)


class CompleteCustomerReturnInspection(SchemaBase):
    line_id: int = Field(ge=1)
    accepted_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    rejected_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    result: InspectionResult
    conclusion: str | None = Field(default=None, max_length=4000)


class ResolveCustomerReturn(SchemaBase):
    resolution_type: CustomerReturnResolution
    resolution_notes: str | None = Field(default=None, max_length=4000)


class CreateAfterSalesOrder(SchemaBase):
    execution_no: str | None = Field(default=None, max_length=100)
    resolution_type: CustomerReturnResolution
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    replacement_material_id: int | None = Field(default=None, ge=1)
    replacement_lot_id: int | None = Field(default=None, ge=1)
    replacement_quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    execution_notes: str | None = Field(default=None, max_length=4000)


class AfterSalesOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_no: str
    return_id: int
    complaint_id: int
    sales_order_id: int | None
    customer_id: int
    resolution_type: CustomerReturnResolution
    material_id: int
    quantity: Decimal
    warehouse_id: int
    location_id: int
    lot_id: int | None
    replacement_material_id: int | None
    replacement_lot_id: int | None
    replacement_quantity: Decimal | None
    status: AfterSalesExecutionStatus
    stock_transaction_id: int | None
    execution_notes: str | None
    completed_at: datetime | None
    sla_due_at: datetime | None
    sla_owner_id: int | None
    created_time: datetime


class AfterSalesAuditDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    after_sales_order_id: int
    action: AfterSalesAuditAction
    from_status: AfterSalesExecutionStatus | None
    to_status: AfterSalesExecutionStatus | None
    notes: str | None
    acted_by: int | None
    acted_at: datetime


class AfterSalesRepairTaskDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_no: str
    after_sales_order_id: int
    status: AfterSalesRepairTaskStatus
    description: str
    result_notes: str | None
    started_at: datetime | None
    completed_at: datetime | None


class CompleteAfterSalesRepairTask(SchemaBase):
    result_notes: str = Field(min_length=1, max_length=4000)


class SlaRuleDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_code: str
    entity_type: SlaEntityType
    target_hours: int
    warning_hours: int
    severity: str | None
    active: int
    default_owner_id: int | None


class WorkItemAlertDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_no: str
    entity_type: SlaEntityType
    entity_id: int
    rule_id: int
    title: str
    due_at: datetime
    status: SlaAlertStatus
    owner_id: int | None
    warning_at: datetime | None
    escalated_at: datetime | None
    escalation_level: int
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class OperationDashboardSummary(SchemaBase):
    status_counts: dict[str, dict[str, int]]
    overdue_counts: dict[str, int]
    average_close_hours: dict[str, float]
    repeated_defects: list[dict[str, str | int]]
    inventory_impact: dict[str, int | float]
    open_alerts: int
    owner_todo_count: int


class EscalateWorkItemAlert(SchemaBase):
    level: int = Field(default=1, ge=1, le=9)
