from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.quality.enums import (
    SupplierCorrectiveActionStatus,
    SupplierCorrectiveVerificationResult,
    SupplierProcurementDecision,
    SupplierQualityGrade,
    SupplierQualityPolicyStatus,
)


class SupplierCorrectiveAction(Base):
    """Supplier corrective-action request (SCAR) raised from an incoming NCR."""

    __tablename__ = 'mes_supplier_corrective_action'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_scar_supplier'),
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_scar_ncr'),
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_scar_inspection'),
        sa.ForeignKeyConstraint(['supplier_receipt_id'], ['erp_supplier_receipt.id'], name='fk_scar_receipt'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_scar_material'),
        sa.ForeignKeyConstraint(['disposition_id'], ['mes_nonconformance_disposition.id'], name='fk_scar_disposition'),
        sa.ForeignKeyConstraint(['reinspection_id'], ['mes_quality_inspection.id'], name='fk_scar_reinspection'),
        sa.UniqueConstraint('scar_no', 'deleted', name='uk_mes_scar_no'),
        sa.UniqueConstraint('ncr_id', 'deleted', name='uk_mes_scar_ncr'),
        sa.Index('idx_mes_scar_supplier_status', 'supplier_id', 'status'),
        sa.Index('idx_mes_scar_due_at', 'due_at'),
        {'comment': 'Supplier corrective action request from incoming quality NCR'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    scar_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    ncr_id: Mapped[int] = mapped_column(sa.BigInteger)
    inspection_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_receipt_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    nonconforming_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    defect_description: Mapped[str] = mapped_column(UniversalText)
    status: Mapped[SupplierCorrectiveActionStatus] = mapped_column(
        sa.String(30), default=SupplierCorrectiveActionStatus.DRAFT,
        server_default=SupplierCorrectiveActionStatus.DRAFT.value,
    )
    severity: Mapped[str] = mapped_column(sa.String(20), default='MAJOR', server_default='MAJOR')
    due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    issued_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    containment_action: Mapped[str | None] = mapped_column(UniversalText, default=None)
    root_cause: Mapped[str | None] = mapped_column(UniversalText, default=None)
    corrective_action: Mapped[str | None] = mapped_column(UniversalText, default=None)
    preventive_action: Mapped[str | None] = mapped_column(UniversalText, default=None)
    response_evidence: Mapped[str | None] = mapped_column(UniversalText, default=None)
    responded_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    disposition_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reinspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    verification_result: Mapped[SupplierCorrectiveVerificationResult | None] = mapped_column(
        sa.String(20), default=None
    )
    verification_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    verified_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    verified_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class SupplierQualityPolicy(Base):
    """Supplier-level scoring thresholds and automatic procurement linkage."""

    __tablename__ = 'mes_supplier_quality_policy'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_quality_policy_supplier'),
        sa.UniqueConstraint('supplier_id', 'deleted', name='uk_supplier_quality_policy_supplier'),
        sa.Index('idx_supplier_quality_policy_status', 'status'),
        {'comment': 'SQM scoring policy and procurement thresholds'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    rolling_days: Mapped[int] = mapped_column(sa.Integer, default=180, server_default='180')
    minimum_inspections: Mapped[int] = mapped_column(sa.Integer, default=1, server_default='1')
    excellent_score: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('95'), server_default='95')
    qualified_score: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('85'), server_default='85')
    conditional_score: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('70'), server_default='70')
    quality_weight: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('70'), server_default='70')
    delivery_weight: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2), default=Decimal('30'), server_default='30')
    auto_apply: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    block_on_open_critical_scar: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    status: Mapped[SupplierQualityPolicyStatus] = mapped_column(
        sa.String(20), default=SupplierQualityPolicyStatus.ACTIVE,
        server_default=SupplierQualityPolicyStatus.ACTIVE.value,
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierQualityAssessment(Base):
    """Immutable supplier quality and delivery score snapshot."""

    __tablename__ = 'mes_supplier_quality_assessment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_quality_assessment_supplier'),
        sa.ForeignKeyConstraint(['policy_id'], ['mes_supplier_quality_policy.id'], name='fk_supplier_quality_assessment_policy'),
        sa.UniqueConstraint('assessment_no', 'deleted', name='uk_supplier_quality_assessment_no'),
        sa.Index('idx_supplier_quality_assessment_supplier', 'supplier_id', 'assessed_at'),
        sa.Index('idx_supplier_quality_assessment_decision', 'procurement_decision'),
        {'comment': 'Supplier quality, corrective action and OTIF score history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    assessment_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    policy_id: Mapped[int] = mapped_column(sa.BigInteger)
    period_start: Mapped[datetime] = mapped_column(TimeZone)
    period_end: Mapped[datetime] = mapped_column(TimeZone)
    assessed_at: Mapped[datetime] = mapped_column(TimeZone)
    grade: Mapped[SupplierQualityGrade] = mapped_column(sa.String(20))
    procurement_decision: Mapped[SupplierProcurementDecision] = mapped_column(sa.String(30))
    overall_score: Mapped[Decimal] = mapped_column(sa.Numeric(5, 2))
    inspection_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    passed_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    failed_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    inspected_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    rejected_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    pass_rate: Mapped[Decimal] = mapped_column(sa.Numeric(7, 2), default=Decimal('0'), server_default='0')
    acceptance_rate: Mapped[Decimal] = mapped_column(sa.Numeric(7, 2), default=Decimal('0'), server_default='0')
    scar_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    scar_closed_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    scar_on_time_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    corrective_score: Mapped[Decimal] = mapped_column(sa.Numeric(7, 2), default=Decimal('0'), server_default='0')
    quality_score: Mapped[Decimal] = mapped_column(sa.Numeric(7, 2), default=Decimal('0'), server_default='0')
    delivery_line_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    otif_line_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    delivery_score: Mapped[Decimal] = mapped_column(sa.Numeric(7, 2), default=Decimal('0'), server_default='0')
    critical_scar_open: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    applied_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    applied_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
