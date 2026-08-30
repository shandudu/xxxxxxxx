from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.supplier.enums import (
    SupplierAuditResult,
    SupplierAuditStatus,
    SupplierAuditType,
    SupplierAvlStatus,
    SupplierPpapStatus,
    SupplierQualificationStatus,
    SupplierReviewDecision,
    SupplierReviewStatus,
    SupplierSampleStatus,
)


class SupplierQualificationApplication(Base):
    """Supplier onboarding application and its final qualification decision."""

    __tablename__ = 'erp_supplier_qualification_application'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_qualification_supplier'),
        sa.UniqueConstraint('application_no', 'deleted', name='uk_supplier_qualification_no'),
        sa.Index('idx_supplier_qualification_supplier_status', 'supplier_id', 'status'),
        sa.Index('idx_supplier_qualification_review_at', 'next_review_at'),
        {'comment': 'Supplier onboarding and qualification application'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    application_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    requested_scope: Mapped[str] = mapped_column(UniversalText)
    status: Mapped[SupplierQualificationStatus] = mapped_column(
        sa.String(30), default=SupplierQualificationStatus.DRAFT,
        server_default=SupplierQualificationStatus.DRAFT.value,
    )
    qualification_level: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    submitted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    decision_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    valid_until: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    next_review_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    certificate_manifest: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierQualificationAudit(Base):
    """Initial, periodic, or special supplier audit."""

    __tablename__ = 'erp_supplier_qualification_audit'
    __table_args__ = (
        sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_audit_application'),
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_audit_supplier'),
        sa.UniqueConstraint('audit_no', 'deleted', name='uk_supplier_audit_no'),
        sa.Index('idx_supplier_audit_application', 'application_id', 'status'),
        sa.Index('idx_supplier_audit_supplier_planned', 'supplier_id', 'planned_at'),
        {'comment': 'Supplier qualification and periodic audit'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    audit_no: Mapped[str] = mapped_column(sa.String(100))
    application_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    audit_type: Mapped[SupplierAuditType] = mapped_column(sa.String(20))
    planned_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[SupplierAuditStatus] = mapped_column(
        sa.String(20), default=SupplierAuditStatus.PLANNED, server_default=SupplierAuditStatus.PLANNED.value
    )
    conducted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    score: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), default=None)
    result: Mapped[SupplierAuditResult | None] = mapped_column(sa.String(20), default=None)
    findings: Mapped[str | None] = mapped_column(UniversalText, default=None)
    corrective_due_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    evidence_manifest: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    auditor_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class SupplierSampleApproval(Base):
    """Material sample submission and approval round for a supplier application."""

    __tablename__ = 'erp_supplier_sample_approval'
    __table_args__ = (
        sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_sample_application'),
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_sample_supplier'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_sample_material'),
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_supplier_sample_inspection'),
        sa.UniqueConstraint('sample_no', 'deleted', name='uk_supplier_sample_no'),
        sa.Index('idx_supplier_sample_application_material', 'application_id', 'material_id'),
        sa.Index('idx_supplier_sample_status', 'status'),
        {'comment': 'Supplier material sample approval rounds'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    sample_no: Mapped[str] = mapped_column(sa.String(100))
    application_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    round_no: Mapped[int] = mapped_column(sa.Integer)
    submitted_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    status: Mapped[SupplierSampleStatus] = mapped_column(
        sa.String(20), default=SupplierSampleStatus.PENDING, server_default=SupplierSampleStatus.PENDING.value
    )
    inspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    submitted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    decision_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    evidence_manifest: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)


class SupplierPpapSubmission(Base):
    """PPAP/APQP evidence package and approval for one supplier material."""

    __tablename__ = 'erp_supplier_ppap_submission'
    __table_args__ = (
        sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_ppap_application'),
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_ppap_supplier'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_ppap_material'),
        sa.ForeignKeyConstraint(['sample_approval_id'], ['erp_supplier_sample_approval.id'], name='fk_supplier_ppap_sample'),
        sa.UniqueConstraint('ppap_no', 'deleted', name='uk_supplier_ppap_no'),
        sa.UniqueConstraint('supplier_id', 'material_id', 'version', 'deleted', name='uk_supplier_ppap_version'),
        sa.Index('idx_supplier_ppap_application_status', 'application_id', 'status'),
        sa.Index('idx_supplier_ppap_expiry', 'expires_at'),
        {'comment': 'Supplier PPAP and APQP approval package'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    ppap_no: Mapped[str] = mapped_column(sa.String(100))
    application_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    level: Mapped[int] = mapped_column(sa.Integer)
    version: Mapped[str] = mapped_column(sa.String(40))
    status: Mapped[SupplierPpapStatus] = mapped_column(
        sa.String(20), default=SupplierPpapStatus.DRAFT, server_default=SupplierPpapStatus.DRAFT.value
    )
    sample_approval_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    document_manifest: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    submitted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    decision_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class SupplierApprovedMaterial(Base):
    """Material-level approved vendor list entry."""

    __tablename__ = 'erp_supplier_approved_material'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_avl_supplier'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_avl_material'),
        sa.ForeignKeyConstraint(['supplier_material_id'], ['erp_supplier_material.id'], name='fk_supplier_avl_relation'),
        sa.ForeignKeyConstraint(['qualification_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_avl_qualification'),
        sa.ForeignKeyConstraint(['ppap_id'], ['erp_supplier_ppap_submission.id'], name='fk_supplier_avl_ppap'),
        sa.UniqueConstraint('supplier_id', 'material_id', 'deleted', name='uk_supplier_avl_supplier_material'),
        sa.Index('idx_supplier_avl_material_status', 'material_id', 'status'),
        sa.Index('idx_supplier_avl_supplier_status', 'supplier_id', 'status'),
        sa.Index('idx_supplier_avl_next_review', 'next_review_at'),
        {'comment': 'Approved vendor list by supplier and material'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    supplier_material_id: Mapped[int] = mapped_column(sa.BigInteger)
    qualification_id: Mapped[int] = mapped_column(sa.BigInteger)
    ppap_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[SupplierAvlStatus] = mapped_column(
        sa.String(20), default=SupplierAvlStatus.APPROVED, server_default=SupplierAvlStatus.APPROVED.value
    )
    approved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    valid_from: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    valid_until: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    last_review_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    next_review_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    restrictions: Mapped[str | None] = mapped_column(UniversalText, default=None)
    approved_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class SupplierPeriodicReview(Base):
    """Periodic AVL review and continue/condition/suspend/remove decision."""

    __tablename__ = 'erp_supplier_periodic_review'
    __table_args__ = (
        sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_review_supplier'),
        sa.ForeignKeyConstraint(['avl_id'], ['erp_supplier_approved_material.id'], name='fk_supplier_review_avl'),
        sa.ForeignKeyConstraint(['quality_assessment_id'], ['mes_supplier_quality_assessment.id'], name='fk_supplier_review_assessment'),
        sa.UniqueConstraint('review_no', 'deleted', name='uk_supplier_review_no'),
        sa.Index('idx_supplier_review_status_planned', 'status', 'planned_at'),
        sa.Index('idx_supplier_review_supplier', 'supplier_id', 'reviewed_at'),
        {'comment': 'Supplier AVL periodic review decision history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    review_no: Mapped[str] = mapped_column(sa.String(100))
    supplier_id: Mapped[int] = mapped_column(sa.BigInteger)
    avl_id: Mapped[int] = mapped_column(sa.BigInteger)
    planned_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[SupplierReviewStatus] = mapped_column(
        sa.String(20), default=SupplierReviewStatus.PLANNED, server_default=SupplierReviewStatus.PLANNED.value
    )
    quality_assessment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    score_snapshot: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), default=None)
    decision: Mapped[SupplierReviewDecision | None] = mapped_column(sa.String(20), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    reviewed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    next_review_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
