from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.plugin.production.enums import AndonEventType, AndonPriority, AndonStatus, WorkOrderStatus


class CreateWorkOrder(SchemaBase):
    work_order_no: str | None = Field(default=None, max_length=100)
    product_material_id: int = Field(ge=1)
    bom_id: int = Field(ge=1)
    routing_id: int = Field(ge=1)
    planned_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)


class WorkOrderOperationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sequence_no: int
    operation_id: int
    operation_code_snapshot: str
    operation_name_snapshot: str
    work_center_id: int | None
    status: str
    completed_quantity: Decimal
    scrap_quantity: Decimal


class WorkOrderRequirementDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    line_no: int
    material_id: int
    unit_id: int
    material_code_snapshot: str
    material_name_snapshot: str
    required_quantity: Decimal
    issued_quantity: Decimal
    returned_quantity: Decimal
    work_order_operation_id: int | None


class WorkOrderMaterialAllocationDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requirement_id: int
    work_order_operation_id: int
    planned_quantity: Decimal


class WorkOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    work_order_no: str
    product_material_id: int
    product_code_snapshot: str
    product_name_snapshot: str
    bom_id: int
    bom_code_snapshot: str
    bom_version_snapshot: str
    routing_id: int
    routing_code_snapshot: str
    routing_version_snapshot: str
    planned_quantity: Decimal
    completed_quantity: Decimal
    scrap_quantity: Decimal
    status: WorkOrderStatus
    planned_start_at: datetime | None
    planned_end_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    remark: str | None
    created_time: datetime
    operations: list[WorkOrderOperationDetail] = Field(default_factory=list)
    requirements: list[WorkOrderRequirementDetail] = Field(default_factory=list)
    material_allocations: list[WorkOrderMaterialAllocationDetail] = Field(default_factory=list)


class MaterialIssueLineConfig(SchemaBase):
    requirement_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class CreateMaterialIssue(SchemaBase):
    issue_no: str | None = Field(default=None, max_length=100)
    work_order_id: int = Field(ge=1)
    remark: str | None = Field(default=None, max_length=500)
    lines: list[MaterialIssueLineConfig] = Field(min_length=1, max_length=500)


class MaterialIssueLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requirement_id: int
    material_id: int
    lot_id: int | None
    warehouse_id: int
    location_id: int
    quantity: Decimal
    returned_quantity: Decimal
    stock_transaction_id: int


class MaterialIssueDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    issue_no: str
    work_order_id: int
    status: str
    remark: str | None
    created_time: datetime
    lines: list[MaterialIssueLineDetail] = Field(default_factory=list)


class MaterialReturnLineConfig(SchemaBase):
    issue_line_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class CreateMaterialReturn(SchemaBase):
    return_no: str | None = Field(default=None, max_length=100)
    work_order_id: int = Field(ge=1)
    remark: str | None = Field(default=None, max_length=500)
    lines: list[MaterialReturnLineConfig] = Field(min_length=1, max_length=500)


class CreateProductionReport(SchemaBase):
    report_no: str | None = Field(default=None, max_length=100)
    work_order_id: int = Field(ge=1)
    good_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    scrap_quantity: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    lot_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)


class PostedDocumentDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str | None = None
    created_time: datetime


class MaterialVarianceDetail(SchemaBase):
    requirement_id: int
    material_id: int
    material_code: str
    material_name: str
    required_quantity: Decimal
    issued_quantity: Decimal
    returned_quantity: Decimal
    actual_quantity: Decimal
    variance_quantity: Decimal
    variance_rate: Decimal | None


class ProductionDashboard(SchemaBase):
    total_orders: int
    draft_orders: int
    released_orders: int
    in_progress_orders: int
    completed_orders: int
    planned_quantity: Decimal
    completed_quantity: Decimal
    completion_rate: Decimal


class CreateAndonEvent(SchemaBase):
    event_type: AndonEventType
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    priority: AndonPriority = AndonPriority.MEDIUM
    work_order_id: int | None = Field(default=None, ge=1)
    work_order_operation_id: int | None = Field(default=None, ge=1)
    equipment_id: int | None = Field(default=None, ge=1)
    material_id: int | None = Field(default=None, ge=1)
    ncr_id: int | None = Field(default=None, ge=1)
    occurred_at: datetime | None = None


class AndonEventDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_no: str
    event_type: AndonEventType
    priority: AndonPriority
    status: AndonStatus
    title: str
    description: str
    work_order_id: int | None
    work_order_operation_id: int | None
    equipment_id: int | None
    material_id: int | None
    ncr_id: int | None
    reporter_id: int | None
    assignee_id: int | None
    occurred_at: datetime
    sla_due_at: datetime
    acknowledged_at: datetime | None
    started_at: datetime | None
    resolved_at: datetime | None
    escalation_level: int
    root_cause: str | None
    resolution_notes: str | None
    created_time: datetime


class AssignAndonEvent(SchemaBase):
    assignee_id: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=2000)


class ResolveAndonEvent(SchemaBase):
    root_cause: str | None = Field(default=None, max_length=4000)
    resolution_notes: str = Field(min_length=1, max_length=4000)


class AndonDashboard(SchemaBase):
    status_counts: dict[str, int]
    type_counts: dict[str, int]
    priority_counts: dict[str, int]
    active_count: int
    overdue_count: int
    average_resolve_hours: Decimal


class AndonAssignmentDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    assignee_id: int
    assigned_by: int | None
    assigned_at: datetime
    accepted_at: datetime | None
    completed_at: datetime | None
    notes: str | None


class AndonActionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    action: str
    from_status: AndonStatus | None
    to_status: AndonStatus | None
    notes: str | None
    acted_by: int | None
    acted_at: datetime
