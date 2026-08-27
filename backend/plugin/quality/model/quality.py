from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.quality.enums import AfterSalesAuditAction, AfterSalesExecutionStatus, AfterSalesRepairTaskStatus, CapaActionStatus, CapaActionType, CapaStatus, CapaVerificationResult, CustomerComplaintStatus, CustomerReturnResolution, CustomerReturnStatus, DispositionStatus, DispositionType, InspectionResult, InspectionStatus, InspectionType, NcrStatus, ReworkStatus, SlaAlertStatus, SlaEntityType


class QualityInspection(Base):
    """Quality inspection supporting incoming, process, final and parent-linked retest flows."""

    __tablename__ = 'mes_quality_inspection'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_quality_inspection_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_quality_inspection_lot'),
        sa.ForeignKeyConstraint(['parent_inspection_id'], ['mes_quality_inspection.id'], name='fk_quality_inspection_parent'),
        sa.UniqueConstraint('inspection_no', 'deleted', name='uk_mes_quality_inspection_no'),
        sa.Index('idx_mes_quality_inspection_type_status', 'inspection_type', 'status'),
        sa.Index('idx_mes_quality_inspection_source', 'source_type', 'source_id'),
        {'comment': 'MES quality inspections'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    inspection_no: Mapped[str] = mapped_column(sa.String(100))
    inspection_type: Mapped[InspectionType] = mapped_column(sa.String(30))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    sample_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    status: Mapped[InspectionStatus] = mapped_column(sa.String(20), default=InspectionStatus.PENDING, server_default=InspectionStatus.PENDING.value)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    parent_inspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_type: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    accepted_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    rejected_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    result: Mapped[InspectionResult | None] = mapped_column(sa.String(20), default=None)
    inspected_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    inspector_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    conclusion: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class NonconformanceReport(Base):
    """NCR raised from a failed or partially accepted inspection."""

    __tablename__ = 'mes_nonconformance_report'
    __table_args__ = (
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_ncr_inspection'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_ncr_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_ncr_lot'),
        sa.UniqueConstraint('ncr_no', 'deleted', name='uk_mes_ncr_no'),
        sa.Index('idx_mes_ncr_status', 'status'),
        {'comment': 'MES nonconformance reports'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    ncr_no: Mapped[str] = mapped_column(sa.String(100))
    inspection_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    nonconforming_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    defect_description: Mapped[str] = mapped_column(UniversalText)
    status: Mapped[NcrStatus] = mapped_column(sa.String(30), default=NcrStatus.OPEN, server_default=NcrStatus.OPEN.value)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    severity: Mapped[str] = mapped_column(sa.String(20), default='MAJOR', server_default='MAJOR')
    root_cause: Mapped[str | None] = mapped_column(UniversalText, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class QualityReworkOrder(Base):
    """Traceable rework task created from an approved NCR disposition."""

    __tablename__ = 'mes_quality_rework_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_quality_rework_ncr'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_quality_rework_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_quality_rework_lot'),
        sa.ForeignKeyConstraint(['production_work_order_id'], ['mes_work_order.id'], name='fk_quality_rework_work_order'),
        sa.ForeignKeyConstraint(['reinspection_id'], ['mes_quality_inspection.id'], name='fk_quality_rework_reinspection'),
        sa.UniqueConstraint('rework_no', 'deleted', name='uk_mes_quality_rework_no'),
        sa.UniqueConstraint('ncr_id', 'deleted', name='uk_mes_quality_rework_ncr'),
        sa.Index('idx_mes_quality_rework_status', 'status'),
        {'comment': 'MES quality rework tasks'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    rework_no: Mapped[str] = mapped_column(sa.String(100))
    ncr_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    production_work_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[ReworkStatus] = mapped_column(
        sa.String(30), default=ReworkStatus.PLANNED, server_default=ReworkStatus.PLANNED.value
    )
    reinspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    released_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class QualityCapa(Base):
    """8D corrective and preventive action case linked to one NCR."""

    __tablename__ = 'mes_quality_capa'
    __table_args__ = (
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_quality_capa_ncr'),
        sa.UniqueConstraint('capa_no', 'deleted', name='uk_mes_quality_capa_no'),
        sa.UniqueConstraint('ncr_id', 'deleted', name='uk_mes_quality_capa_ncr'),
        sa.Index('idx_mes_quality_capa_status', 'status'),
        {'comment': 'MES quality CAPA / 8D cases'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    capa_no: Mapped[str] = mapped_column(sa.String(100))
    ncr_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[CapaStatus] = mapped_column(sa.String(30), default=CapaStatus.OPEN, server_default=CapaStatus.OPEN.value)
    d1_team_summary: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d2_problem_description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d3_containment_summary: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d4_root_cause: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d5_corrective_plan: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d6_implementation_summary: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d7_prevention_summary: Mapped[str | None] = mapped_column(UniversalText, default=None)
    d8_closure_summary: Mapped[str | None] = mapped_column(UniversalText, default=None)
    owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class QualityCapaAction(Base):
    """Containment, corrective or preventive action under a CAPA case."""

    __tablename__ = 'mes_quality_capa_action'
    __table_args__ = (
        sa.ForeignKeyConstraint(['capa_id'], ['mes_quality_capa.id'], name='fk_quality_capa_action_capa'),
        sa.UniqueConstraint('action_no', 'deleted', name='uk_mes_quality_capa_action_no'),
        sa.Index('idx_mes_quality_capa_action_status', 'capa_id', 'status'),
        {'comment': 'MES CAPA action items'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    action_no: Mapped[str] = mapped_column(sa.String(100))
    capa_id: Mapped[int] = mapped_column(sa.BigInteger)
    action_type: Mapped[CapaActionType] = mapped_column(sa.String(30))
    description: Mapped[str] = mapped_column(UniversalText)
    owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    status: Mapped[CapaActionStatus] = mapped_column(sa.String(30), default=CapaActionStatus.OPEN, server_default=CapaActionStatus.OPEN.value)
    evidence: Mapped[str | None] = mapped_column(UniversalText, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    verified_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class QualityCapaVerification(Base):
    """Immutable effectiveness verification record for a CAPA case."""

    __tablename__ = 'mes_quality_capa_verification'
    __table_args__ = (
        sa.ForeignKeyConstraint(['capa_id'], ['mes_quality_capa.id'], name='fk_quality_capa_verification_capa'),
        sa.Index('idx_mes_quality_capa_verification_capa', 'capa_id', 'verified_at'),
        {'comment': 'MES CAPA effectiveness verification history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    capa_id: Mapped[int] = mapped_column(sa.BigInteger)
    result: Mapped[CapaVerificationResult] = mapped_column(sa.String(20))
    verified_at: Mapped[datetime] = mapped_column(TimeZone)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    verified_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class CustomerComplaint(Base):
    """Customer complaint case that can create an RMA, NCR and CAPA."""

    __tablename__ = 'erp_customer_complaint'
    __table_args__ = (
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_customer_complaint_customer'),
        sa.ForeignKeyConstraint(['sales_order_id'], ['erp_sales_order.id'], name='fk_customer_complaint_order'),
        sa.ForeignKeyConstraint(['shipment_id'], ['erp_shipment.id'], name='fk_customer_complaint_shipment'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_customer_complaint_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_customer_complaint_lot'),
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_customer_complaint_ncr'),
        sa.ForeignKeyConstraint(['capa_id'], ['mes_quality_capa.id'], name='fk_customer_complaint_capa'),
        sa.UniqueConstraint('complaint_no', 'deleted', name='uk_erp_customer_complaint_no'),
        sa.Index('idx_erp_customer_complaint_status', 'status'),
        sa.Index('idx_erp_customer_complaint_customer', 'customer_id'),
        {'comment': 'ERP customer complaints linked to quality closure'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    complaint_no: Mapped[str] = mapped_column(sa.String(100))
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    customer_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    customer_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    title: Mapped[str] = mapped_column(sa.String(200))
    description: Mapped[str] = mapped_column(UniversalText)
    sales_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    shipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    status: Mapped[CustomerComplaintStatus] = mapped_column(sa.String(30), default=CustomerComplaintStatus.OPEN, server_default=CustomerComplaintStatus.OPEN.value)
    rma_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    ncr_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    capa_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    resolution_type: Mapped[CustomerReturnResolution | None] = mapped_column(sa.String(30), default=None)
    resolution_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class CustomerReturn(Base):
    """Authorized customer return header and quality outcome."""

    __tablename__ = 'erp_customer_return'
    __table_args__ = (
        sa.ForeignKeyConstraint(['complaint_id'], ['erp_customer_complaint.id'], name='fk_customer_return_complaint'),
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_customer_return_customer'),
        sa.ForeignKeyConstraint(['shipment_id'], ['erp_shipment.id'], name='fk_customer_return_shipment'),
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_customer_return_ncr'),
        sa.UniqueConstraint('return_no', 'deleted', name='uk_erp_customer_return_no'),
        sa.Index('idx_erp_customer_return_status', 'status'),
        {'comment': 'ERP customer return/RMA headers'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    return_no: Mapped[str] = mapped_column(sa.String(100))
    complaint_id: Mapped[int] = mapped_column(sa.BigInteger)
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    shipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[CustomerReturnStatus] = mapped_column(sa.String(30), default=CustomerReturnStatus.DRAFT, server_default=CustomerReturnStatus.DRAFT.value)
    ncr_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    resolution_type: Mapped[CustomerReturnResolution | None] = mapped_column(sa.String(30), default=None)
    resolution_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    received_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    inspected_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class CustomerReturnLine(Base):
    """Returned shipment line with stock receipt and inspection links."""

    __tablename__ = 'erp_customer_return_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['return_id'], ['erp_customer_return.id'], name='fk_customer_return_line_return'),
        sa.ForeignKeyConstraint(['shipment_line_id'], ['erp_shipment_line.id'], name='fk_customer_return_line_shipment'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_customer_return_line_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_customer_return_line_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_customer_return_line_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_customer_return_line_location'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_customer_return_line_stock_tx'),
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_customer_return_line_inspection'),
        sa.UniqueConstraint('return_id', 'line_no', 'deleted', name='uk_erp_customer_return_line_no'),
        sa.Index('idx_erp_customer_return_line_status', 'return_id', 'inspection_id'),
        {'comment': 'ERP customer return lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    return_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    shipment_line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    stock_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    inspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class CustomerAfterSalesOrder(Base):
    """Executable customer resolution order generated from a closed RMA decision."""

    __tablename__ = 'erp_customer_after_sales_order'
    __table_args__ = (
        sa.ForeignKeyConstraint(['return_id'], ['erp_customer_return.id'], name='fk_after_sales_return'),
        sa.ForeignKeyConstraint(['complaint_id'], ['erp_customer_complaint.id'], name='fk_after_sales_complaint'),
        sa.ForeignKeyConstraint(['sales_order_id'], ['erp_sales_order.id'], name='fk_after_sales_sales_order'),
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_after_sales_customer'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_after_sales_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_after_sales_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_after_sales_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_after_sales_location'),
        sa.ForeignKeyConstraint(['replacement_material_id'], ['mes_material.id'], name='fk_after_sales_replacement_material'),
        sa.ForeignKeyConstraint(['replacement_lot_id'], ['mes_material_lot.id'], name='fk_after_sales_replacement_lot'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_after_sales_stock_tx'),
        sa.UniqueConstraint('execution_no', 'deleted', name='uk_after_sales_execution_no'),
        sa.UniqueConstraint('return_id', 'resolution_type', 'deleted', name='uk_after_sales_return_resolution'),
        sa.Index('idx_after_sales_status', 'status'),
        sa.Index('idx_after_sales_customer', 'customer_id', 'created_time'),
        {'comment': 'ERP executable customer after-sales resolution orders'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    execution_no: Mapped[str] = mapped_column(sa.String(100))
    return_id: Mapped[int] = mapped_column(sa.BigInteger)
    complaint_id: Mapped[int] = mapped_column(sa.BigInteger)
    customer_id: Mapped[int] = mapped_column(sa.BigInteger)
    resolution_type: Mapped[CustomerReturnResolution] = mapped_column(sa.String(30))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    sales_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    replacement_material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    replacement_lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    replacement_quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    status: Mapped[AfterSalesExecutionStatus] = mapped_column(sa.String(30), default=AfterSalesExecutionStatus.DRAFT, server_default=AfterSalesExecutionStatus.DRAFT.value)
    stock_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    execution_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    sla_owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class CustomerAfterSalesRepairTask(Base):
    """Repair task for returned products that require service before closure."""

    __tablename__ = 'erp_customer_after_sales_repair_task'
    __table_args__ = (
        sa.ForeignKeyConstraint(['after_sales_order_id'], ['erp_customer_after_sales_order.id'], name='fk_after_sales_repair_order'),
        sa.UniqueConstraint('task_no', 'deleted', name='uk_after_sales_repair_task_no'),
        sa.Index('idx_after_sales_repair_task_status', 'status'),
        {'comment': 'ERP customer after-sales repair tasks'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    task_no: Mapped[str] = mapped_column(sa.String(100))
    after_sales_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    description: Mapped[str] = mapped_column(UniversalText)
    status: Mapped[AfterSalesRepairTaskStatus] = mapped_column(sa.String(30), default=AfterSalesRepairTaskStatus.OPEN, server_default=AfterSalesRepairTaskStatus.OPEN.value)
    result_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class CustomerAfterSalesAudit(Base):
    """Append-only audit trail for after-sales execution state and side effects."""

    __tablename__ = 'erp_customer_after_sales_audit'
    __table_args__ = (
        sa.ForeignKeyConstraint(['after_sales_order_id'], ['erp_customer_after_sales_order.id'], name='fk_after_sales_audit_order'),
        sa.Index('idx_after_sales_audit_order_time', 'after_sales_order_id', 'acted_at'),
        {'comment': 'ERP customer after-sales execution audit trail'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    after_sales_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    action: Mapped[AfterSalesAuditAction] = mapped_column(sa.String(30))
    acted_at: Mapped[datetime] = mapped_column(TimeZone)
    from_status: Mapped[AfterSalesExecutionStatus | None] = mapped_column(sa.String(30), default=None)
    to_status: Mapped[AfterSalesExecutionStatus | None] = mapped_column(sa.String(30), default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    acted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class NonconformanceDisposition(Base):
    """Approved MRB quantity split and its execution audit fields."""

    __tablename__ = 'mes_nonconformance_disposition'
    __table_args__ = (
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_mrb_ncr'),
        sa.ForeignKeyConstraint(['rework_order_id'], ['mes_quality_rework_order.id'], name='fk_mrb_rework_order'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_mrb_stock_tx'),
        sa.ForeignKeyConstraint(['reinspection_id'], ['mes_quality_inspection.id'], name='fk_mrb_reinspection'),
        sa.UniqueConstraint('disposition_no', 'deleted', name='uk_mes_mrb_no'),
        sa.Index('idx_mes_mrb_ncr_status', 'ncr_id', 'status'),
        {'comment': 'MES MRB nonconformance dispositions'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    disposition_no: Mapped[str] = mapped_column(sa.String(100))
    ncr_id: Mapped[int] = mapped_column(sa.BigInteger)
    disposition_type: Mapped[DispositionType] = mapped_column(sa.String(40))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    status: Mapped[DispositionStatus] = mapped_column(sa.String(20), default=DispositionStatus.APPROVED, server_default=DispositionStatus.APPROVED.value)
    warehouse_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    location_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    stock_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reinspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    rework_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    decision_reason: Mapped[str | None] = mapped_column(UniversalText, default=None)
    executed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    executed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class QualitySlaRule(Base):
    """Configurable response/closure SLA used by the quality operations dashboard."""

    __tablename__ = 'mes_quality_sla_rule'
    __table_args__ = (
        sa.UniqueConstraint('rule_code', 'deleted', name='uk_quality_sla_rule_code'),
        sa.Index('idx_quality_sla_rule_entity_active', 'entity_type', 'active'),
        {'comment': 'Quality and after-sales SLA rules'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    rule_code: Mapped[str] = mapped_column(sa.String(80))
    entity_type: Mapped[SlaEntityType] = mapped_column(sa.String(30))
    target_hours: Mapped[int] = mapped_column(sa.Integer)
    warning_hours: Mapped[int] = mapped_column(sa.Integer)
    severity: Mapped[str | None] = mapped_column(sa.String(20), default=None)
    active: Mapped[int] = mapped_column(sa.SmallInteger, default=1, server_default='1')
    default_owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class QualityWorkItemAlert(Base):
    """Materialized SLA alert and ownership/escalation state for one work item."""

    __tablename__ = 'mes_quality_work_item_alert'
    __table_args__ = (
        sa.ForeignKeyConstraint(['rule_id'], ['mes_quality_sla_rule.id'], name='fk_quality_alert_rule'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'rule_id', 'deleted', name='uk_quality_alert_work_item'),
        sa.Index('idx_quality_alert_status_due', 'status', 'due_at'),
        sa.Index('idx_quality_alert_owner_status', 'owner_id', 'status'),
        {'comment': 'Quality operations SLA alerts and escalation state'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    alert_no: Mapped[str] = mapped_column(sa.String(100))
    entity_type: Mapped[SlaEntityType] = mapped_column(sa.String(30))
    entity_id: Mapped[int] = mapped_column(sa.BigInteger)
    rule_id: Mapped[int] = mapped_column(sa.BigInteger)
    title: Mapped[str] = mapped_column(sa.String(255))
    due_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[SlaAlertStatus] = mapped_column(sa.String(20), default=SlaAlertStatus.OPEN, server_default=SlaAlertStatus.OPEN.value)
    owner_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    warning_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    escalated_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    escalation_level: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    acknowledged_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    last_notified_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class QualityWorkItemAlertEvent(Base):
    """Append-only acknowledgement/escalation/closure history for an SLA alert."""

    __tablename__ = 'mes_quality_work_item_alert_event'
    __table_args__ = (
        sa.ForeignKeyConstraint(['alert_id'], ['mes_quality_work_item_alert.id'], name='fk_quality_alert_event_alert'),
        sa.Index('idx_quality_alert_event_alert_time', 'alert_id', 'acted_at'),
        {'comment': 'Quality SLA alert action history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    alert_id: Mapped[int] = mapped_column(sa.BigInteger)
    action: Mapped[str] = mapped_column(sa.String(30))
    acted_at: Mapped[datetime] = mapped_column(TimeZone)
    from_status: Mapped[SlaAlertStatus | None] = mapped_column(sa.String(20), default=None)
    to_status: Mapped[SlaAlertStatus | None] = mapped_column(sa.String(20), default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    acted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
