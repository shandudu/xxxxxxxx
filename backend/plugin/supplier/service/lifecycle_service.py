from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.material.model import Material
from backend.plugin.quality.enums import InspectionResult, InspectionStatus
from backend.plugin.quality.model import QualityInspection, SupplierQualityAssessment
from backend.plugin.supplier.enums import (
    CooperationStatus,
    SupplierAuditResult,
    SupplierAuditStatus,
    SupplierAvlStatus,
    SupplierMaterialStatus,
    SupplierPpapStatus,
    SupplierQualificationStatus,
    SupplierQualityStatus,
    SupplierReviewDecision,
    SupplierReviewStatus,
    SupplierSampleStatus,
    SupplierStatus,
)
from backend.plugin.supplier.model import (
    Supplier,
    SupplierApprovedMaterial,
    SupplierMaterial,
    SupplierPeriodicReview,
    SupplierPpapSubmission,
    SupplierQualificationApplication,
    SupplierQualificationAudit,
    SupplierSampleApproval,
)
from backend.plugin.supplier.schema.lifecycle import (
    ApprovedMaterialDetail,
    CompletePeriodicReview,
    CompleteQualificationAudit,
    CreatePeriodicReview,
    CreatePpapSubmission,
    CreateQualificationApplication,
    CreateQualificationAudit,
    CreateSampleApproval,
    DecidePpapSubmission,
    DecideSampleApproval,
    PeriodicReviewDetail,
    PpapSubmissionDetail,
    QualificationApplicationDetail,
    QualificationAuditDetail,
    QualificationDecision,
    RejectQualification,
    SampleApprovalDetail,
    SupplierLifecycleDashboard,
)
from backend.utils.timezone import timezone


class SupplierLifecycleService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _number(prefix: str) -> str:
        return f'{prefix}-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper()

    @staticmethod
    async def _supplier(db: AsyncSession, supplier_id: int, lock: bool = False) -> Supplier:
        stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        supplier = await db.scalar(stmt)
        if not supplier:
            raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
        return supplier

    @staticmethod
    async def _application(db: AsyncSession, application_id: int, lock: bool = False) -> SupplierQualificationApplication:
        stmt = select(SupplierQualificationApplication).where(
            SupplierQualificationApplication.id == application_id,
            SupplierQualificationApplication.deleted == 0,
        )
        if lock:
            stmt = stmt.with_for_update()
        application = await db.scalar(stmt)
        if not application:
            raise errors.NotFoundError(msg='SUPPLIER_QUALIFICATION_NOT_FOUND')
        return application

    @staticmethod
    async def dashboard(db: AsyncSession) -> SupplierLifecycleDashboard:
        now = timezone.now()
        soon = now + timedelta(days=30)

        async def count(model, *conditions) -> int:
            return int(await db.scalar(select(func.count(model.id)).where(model.deleted == 0, *conditions)) or 0)

        return SupplierLifecycleDashboard(
            draft_applications=await count(
                SupplierQualificationApplication,
                SupplierQualificationApplication.status == SupplierQualificationStatus.DRAFT,
            ),
            pending_applications=await count(
                SupplierQualificationApplication,
                SupplierQualificationApplication.status.in_((
                    SupplierQualificationStatus.SUBMITTED,
                    SupplierQualificationStatus.UNDER_REVIEW,
                )),
            ),
            audits_pending=await count(
                SupplierQualificationAudit, SupplierQualificationAudit.status == SupplierAuditStatus.PLANNED
            ),
            samples_pending=await count(
                SupplierSampleApproval,
                SupplierSampleApproval.status.in_((SupplierSampleStatus.PENDING, SupplierSampleStatus.TESTING)),
            ),
            ppaps_pending=await count(
                SupplierPpapSubmission,
                SupplierPpapSubmission.status.in_((SupplierPpapStatus.DRAFT, SupplierPpapStatus.SUBMITTED)),
            ),
            active_avl_entries=await count(
                SupplierApprovedMaterial,
                SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
                or_(SupplierApprovedMaterial.valid_until.is_(None), SupplierApprovedMaterial.valid_until >= now),
            ),
            avl_expiring_soon=await count(
                SupplierApprovedMaterial,
                SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
                SupplierApprovedMaterial.valid_until.between(now, soon),
            ),
            reviews_due=await count(
                SupplierApprovedMaterial,
                SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
                SupplierApprovedMaterial.next_review_at <= now,
            ),
            suspended_or_removed=await count(
                SupplierApprovedMaterial,
                SupplierApprovedMaterial.status.in_((SupplierAvlStatus.SUSPENDED, SupplierAvlStatus.REMOVED)),
            ),
        )

    @staticmethod
    async def list_applications(
        db: AsyncSession, supplier_id: int | None = None, status: SupplierQualificationStatus | None = None
    ) -> list[QualificationApplicationDetail]:
        stmt = select(SupplierQualificationApplication).where(SupplierQualificationApplication.deleted == 0)
        if supplier_id is not None:
            stmt = stmt.where(SupplierQualificationApplication.supplier_id == supplier_id)
        if status is not None:
            stmt = stmt.where(SupplierQualificationApplication.status == status)
        rows = (await db.scalars(stmt.order_by(SupplierQualificationApplication.id.desc()))).all()
        return [QualificationApplicationDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_application(db: AsyncSession, obj: CreateQualificationApplication) -> QualificationApplicationDetail:
        supplier = await SupplierLifecycleService._supplier(db, obj.supplier_id, lock=True)
        active = await db.scalar(select(SupplierQualificationApplication.id).where(
            SupplierQualificationApplication.supplier_id == supplier.id,
            SupplierQualificationApplication.deleted == 0,
            SupplierQualificationApplication.status.in_((
                SupplierQualificationStatus.DRAFT,
                SupplierQualificationStatus.SUBMITTED,
                SupplierQualificationStatus.UNDER_REVIEW,
                SupplierQualificationStatus.APPROVED,
            )),
        ))
        if active:
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_ALREADY_ACTIVE')
        row = SupplierQualificationApplication(
            application_no=SupplierLifecycleService._number('SQA'),
            supplier_id=supplier.id,
            requested_scope=obj.requested_scope,
            certificate_manifest=obj.certificate_manifest,
            remark=obj.remark,
        )
        db.add(row)
        supplier.quality_status = SupplierQualityStatus.PENDING
        supplier.purchasing_enabled = False
        await db.flush()
        return QualificationApplicationDetail.model_validate(row)

    @staticmethod
    async def submit_application(db: AsyncSession, application_id: int) -> QualificationApplicationDetail:
        row = await SupplierLifecycleService._application(db, application_id, lock=True)
        if row.status != SupplierQualificationStatus.DRAFT:
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_DRAFT')
        if not row.certificate_manifest:
            raise errors.ConflictError(msg='SUPPLIER_CERTIFICATES_REQUIRED')
        row.status = SupplierQualificationStatus.SUBMITTED
        row.submitted_at = timezone.now()
        await db.flush()
        return QualificationApplicationDetail.model_validate(row)

    @staticmethod
    async def reject_application(
        db: AsyncSession, application_id: int, obj: RejectQualification
    ) -> QualificationApplicationDetail:
        row = await SupplierLifecycleService._application(db, application_id, lock=True)
        if row.status not in (SupplierQualificationStatus.SUBMITTED, SupplierQualificationStatus.UNDER_REVIEW):
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_REVIEWABLE')
        supplier = await SupplierLifecycleService._supplier(db, row.supplier_id, lock=True)
        now = timezone.now()
        row.status = SupplierQualificationStatus.REJECTED
        row.decided_at = now
        row.decided_by = SupplierLifecycleService._operator_id()
        row.decision_notes = obj.decision_notes
        supplier.quality_status = SupplierQualityStatus.UNQUALIFIED
        supplier.purchasing_enabled = False
        await db.flush()
        return QualificationApplicationDetail.model_validate(row)

    @staticmethod
    async def list_audits(db: AsyncSession, application_id: int | None = None) -> list[QualificationAuditDetail]:
        stmt = select(SupplierQualificationAudit).where(SupplierQualificationAudit.deleted == 0)
        if application_id is not None:
            stmt = stmt.where(SupplierQualificationAudit.application_id == application_id)
        rows = (await db.scalars(stmt.order_by(SupplierQualificationAudit.id.desc()))).all()
        return [QualificationAuditDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_audit(
        db: AsyncSession, application_id: int, obj: CreateQualificationAudit
    ) -> QualificationAuditDetail:
        application = await SupplierLifecycleService._application(db, application_id, lock=True)
        if application.status not in (SupplierQualificationStatus.SUBMITTED, SupplierQualificationStatus.UNDER_REVIEW):
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_REVIEWABLE')
        row = SupplierQualificationAudit(
            audit_no=SupplierLifecycleService._number('SAU'), application_id=application.id,
            supplier_id=application.supplier_id, audit_type=obj.audit_type, planned_at=obj.planned_at,
            remark=obj.remark,
        )
        db.add(row)
        application.status = SupplierQualificationStatus.UNDER_REVIEW
        await db.flush()
        return QualificationAuditDetail.model_validate(row)

    @staticmethod
    async def complete_audit(
        db: AsyncSession, audit_id: int, obj: CompleteQualificationAudit
    ) -> QualificationAuditDetail:
        row = await db.scalar(select(SupplierQualificationAudit).where(
            SupplierQualificationAudit.id == audit_id, SupplierQualificationAudit.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='SUPPLIER_AUDIT_NOT_FOUND')
        if row.status != SupplierAuditStatus.PLANNED:
            raise errors.ConflictError(msg='SUPPLIER_AUDIT_NOT_PLANNED')
        if obj.result == SupplierAuditResult.CONDITIONAL and obj.corrective_due_at is None:
            raise errors.RequestError(msg='SUPPLIER_AUDIT_CORRECTIVE_DUE_REQUIRED')
        row.status = SupplierAuditStatus.COMPLETED
        row.conducted_at = timezone.now()
        row.score = obj.score
        row.result = obj.result
        row.findings = obj.findings
        row.corrective_due_at = obj.corrective_due_at
        row.evidence_manifest = obj.evidence_manifest
        row.auditor_id = SupplierLifecycleService._operator_id()
        await db.flush()
        return QualificationAuditDetail.model_validate(row)

    @staticmethod
    async def list_samples(db: AsyncSession, application_id: int | None = None) -> list[SampleApprovalDetail]:
        stmt = select(SupplierSampleApproval).where(SupplierSampleApproval.deleted == 0)
        if application_id is not None:
            stmt = stmt.where(SupplierSampleApproval.application_id == application_id)
        rows = (await db.scalars(stmt.order_by(SupplierSampleApproval.id.desc()))).all()
        return [SampleApprovalDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_sample(
        db: AsyncSession, application_id: int, obj: CreateSampleApproval
    ) -> SampleApprovalDetail:
        application = await SupplierLifecycleService._application(db, application_id, lock=True)
        if application.status not in (SupplierQualificationStatus.SUBMITTED, SupplierQualificationStatus.UNDER_REVIEW):
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_REVIEWABLE')
        material = await db.scalar(select(Material).where(Material.id == obj.material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        round_no = int(await db.scalar(select(func.count(SupplierSampleApproval.id)).where(
            SupplierSampleApproval.application_id == application.id,
            SupplierSampleApproval.material_id == material.id,
            SupplierSampleApproval.deleted == 0,
        )) or 0) + 1
        row = SupplierSampleApproval(
            sample_no=SupplierLifecycleService._number('SAM'), application_id=application.id,
            supplier_id=application.supplier_id, material_id=material.id, round_no=round_no,
            submitted_quantity=obj.submitted_quantity, inspection_id=obj.inspection_id,
            submitted_at=timezone.now(), evidence_manifest=obj.evidence_manifest,
        )
        db.add(row)
        application.status = SupplierQualificationStatus.UNDER_REVIEW
        await db.flush()
        return SampleApprovalDetail.model_validate(row)

    @staticmethod
    async def decide_sample(
        db: AsyncSession, sample_id: int, obj: DecideSampleApproval
    ) -> SampleApprovalDetail:
        row = await db.scalar(select(SupplierSampleApproval).where(
            SupplierSampleApproval.id == sample_id, SupplierSampleApproval.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='SUPPLIER_SAMPLE_NOT_FOUND')
        if row.status not in (SupplierSampleStatus.PENDING, SupplierSampleStatus.TESTING):
            raise errors.ConflictError(msg='SUPPLIER_SAMPLE_ALREADY_DECIDED')
        inspection_id = obj.inspection_id or row.inspection_id
        if inspection_id is not None:
            inspection = await db.scalar(select(QualityInspection).where(
                QualityInspection.id == inspection_id, QualityInspection.deleted == 0
            ))
            if not inspection or inspection.material_id != row.material_id:
                raise errors.ConflictError(msg='SUPPLIER_SAMPLE_INSPECTION_MISMATCH')
            if inspection.status != InspectionStatus.COMPLETED:
                raise errors.ConflictError(msg='SUPPLIER_SAMPLE_INSPECTION_NOT_COMPLETED')
            if obj.approved and inspection.result != InspectionResult.PASS:
                raise errors.ConflictError(msg='SUPPLIER_SAMPLE_INSPECTION_NOT_PASSED')
            row.inspection_id = inspection.id
        row.status = SupplierSampleStatus.APPROVED if obj.approved else SupplierSampleStatus.REJECTED
        row.decided_at = timezone.now()
        row.decided_by = SupplierLifecycleService._operator_id()
        row.decision_notes = obj.decision_notes
        await db.flush()
        return SampleApprovalDetail.model_validate(row)

    @staticmethod
    async def list_ppaps(db: AsyncSession, application_id: int | None = None) -> list[PpapSubmissionDetail]:
        stmt = select(SupplierPpapSubmission).where(SupplierPpapSubmission.deleted == 0)
        if application_id is not None:
            stmt = stmt.where(SupplierPpapSubmission.application_id == application_id)
        rows = (await db.scalars(stmt.order_by(SupplierPpapSubmission.id.desc()))).all()
        return [PpapSubmissionDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_ppap(
        db: AsyncSession, application_id: int, obj: CreatePpapSubmission
    ) -> PpapSubmissionDetail:
        application = await SupplierLifecycleService._application(db, application_id, lock=True)
        if application.status not in (SupplierQualificationStatus.SUBMITTED, SupplierQualificationStatus.UNDER_REVIEW):
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_REVIEWABLE')
        material = await db.scalar(select(Material).where(Material.id == obj.material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        sample = None
        if obj.sample_approval_id is not None:
            sample = await db.scalar(select(SupplierSampleApproval).where(
                SupplierSampleApproval.id == obj.sample_approval_id,
                SupplierSampleApproval.deleted == 0,
            ))
            if not sample or sample.application_id != application.id or sample.material_id != obj.material_id:
                raise errors.ConflictError(msg='SUPPLIER_PPAP_SAMPLE_MISMATCH')
        row = SupplierPpapSubmission(
            ppap_no=SupplierLifecycleService._number('PPAP'), application_id=application.id,
            supplier_id=application.supplier_id, material_id=obj.material_id, level=obj.level,
            version=obj.version.strip().upper(), sample_approval_id=obj.sample_approval_id,
            document_manifest=obj.document_manifest,
        )
        db.add(row)
        application.status = SupplierQualificationStatus.UNDER_REVIEW
        await db.flush()
        return PpapSubmissionDetail.model_validate(row)

    @staticmethod
    async def submit_ppap(db: AsyncSession, ppap_id: int) -> PpapSubmissionDetail:
        row = await db.scalar(select(SupplierPpapSubmission).where(
            SupplierPpapSubmission.id == ppap_id, SupplierPpapSubmission.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='SUPPLIER_PPAP_NOT_FOUND')
        if row.status != SupplierPpapStatus.DRAFT:
            raise errors.ConflictError(msg='SUPPLIER_PPAP_NOT_DRAFT')
        if not row.document_manifest:
            raise errors.ConflictError(msg='SUPPLIER_PPAP_DOCUMENTS_REQUIRED')
        row.status = SupplierPpapStatus.SUBMITTED
        row.submitted_at = timezone.now()
        await db.flush()
        return PpapSubmissionDetail.model_validate(row)

    @staticmethod
    async def decide_ppap(
        db: AsyncSession, ppap_id: int, obj: DecidePpapSubmission
    ) -> PpapSubmissionDetail:
        row = await db.scalar(select(SupplierPpapSubmission).where(
            SupplierPpapSubmission.id == ppap_id, SupplierPpapSubmission.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='SUPPLIER_PPAP_NOT_FOUND')
        if row.status != SupplierPpapStatus.SUBMITTED:
            raise errors.ConflictError(msg='SUPPLIER_PPAP_NOT_SUBMITTED')
        if obj.approved:
            sample = await db.scalar(select(SupplierSampleApproval).where(
                SupplierSampleApproval.id == row.sample_approval_id,
                SupplierSampleApproval.status == SupplierSampleStatus.APPROVED,
                SupplierSampleApproval.deleted == 0,
            )) if row.sample_approval_id else None
            if not sample or sample.material_id != row.material_id:
                raise errors.ConflictError(msg='SUPPLIER_PPAP_APPROVED_SAMPLE_REQUIRED')
        now = timezone.now()
        row.status = SupplierPpapStatus.APPROVED if obj.approved else SupplierPpapStatus.REJECTED
        row.decided_at = now
        row.decided_by = SupplierLifecycleService._operator_id()
        row.decision_notes = obj.decision_notes
        if obj.approved:
            row.approved_at = now
            row.expires_at = now + timedelta(days=obj.valid_days)
        await db.flush()
        return PpapSubmissionDetail.model_validate(row)

    @staticmethod
    async def approve_application(
        db: AsyncSession, application_id: int, obj: QualificationDecision
    ) -> QualificationApplicationDetail:
        application = await SupplierLifecycleService._application(db, application_id, lock=True)
        if application.status not in (SupplierQualificationStatus.SUBMITTED, SupplierQualificationStatus.UNDER_REVIEW):
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_REVIEWABLE')
        audit = await db.scalar(select(SupplierQualificationAudit).where(
            SupplierQualificationAudit.application_id == application.id,
            SupplierQualificationAudit.status == SupplierAuditStatus.COMPLETED,
            SupplierQualificationAudit.result.in_((SupplierAuditResult.PASS, SupplierAuditResult.CONDITIONAL)),
            SupplierQualificationAudit.deleted == 0,
        ).order_by(SupplierQualificationAudit.conducted_at.desc(), SupplierQualificationAudit.id.desc()))
        if not audit:
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_AUDIT_REQUIRED')
        ppaps = (await db.scalars(select(SupplierPpapSubmission).where(
            SupplierPpapSubmission.application_id == application.id,
            SupplierPpapSubmission.status == SupplierPpapStatus.APPROVED,
            SupplierPpapSubmission.deleted == 0,
        ).order_by(SupplierPpapSubmission.id.desc()))).all()
        if not ppaps:
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_PPAP_REQUIRED')
        now = timezone.now()
        valid_until = now + timedelta(days=obj.valid_days)
        supplier = await SupplierLifecycleService._supplier(db, application.supplier_id, lock=True)
        conditional_approval = audit.result == SupplierAuditResult.CONDITIONAL
        seen_materials: set[int] = set()
        for ppap in ppaps:
            if ppap.material_id in seen_materials:
                continue
            seen_materials.add(ppap.material_id)
            sample = await db.scalar(select(SupplierSampleApproval).where(
                SupplierSampleApproval.id == ppap.sample_approval_id,
                SupplierSampleApproval.status == SupplierSampleStatus.APPROVED,
                SupplierSampleApproval.deleted == 0,
            ))
            if not sample:
                raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_SAMPLE_REQUIRED')
            relation = await db.scalar(select(SupplierMaterial).where(
                SupplierMaterial.supplier_id == supplier.id,
                SupplierMaterial.material_id == ppap.material_id,
                SupplierMaterial.deleted == 0,
            ).with_for_update())
            if relation is None:
                relation = SupplierMaterial(
                    supplier_id=supplier.id, material_id=ppap.material_id,
                    quality_inspection_required=True,
                )
                db.add(relation)
                await db.flush()
            else:
                relation.status = SupplierMaterialStatus.ACTIVE
                relation.quality_inspection_required = True
            avl = await db.scalar(select(SupplierApprovedMaterial).where(
                SupplierApprovedMaterial.supplier_id == supplier.id,
                SupplierApprovedMaterial.material_id == ppap.material_id,
                SupplierApprovedMaterial.deleted == 0,
            ).with_for_update())
            entry_until = min(valid_until, ppap.expires_at) if ppap.expires_at else valid_until
            if avl is None:
                avl = SupplierApprovedMaterial(
                    supplier_id=supplier.id, material_id=ppap.material_id,
                    supplier_material_id=relation.id, qualification_id=application.id, ppap_id=ppap.id,
                    status=SupplierAvlStatus.CONDITIONAL if conditional_approval else SupplierAvlStatus.APPROVED,
                    approved_at=now, valid_from=now - timedelta(seconds=1), valid_until=entry_until,
                    next_review_at=entry_until,
                    restrictions=audit.findings if conditional_approval else None,
                    approved_by=SupplierLifecycleService._operator_id(),
                )
                db.add(avl)
            else:
                avl.supplier_material_id = relation.id
                avl.qualification_id = application.id
                avl.ppap_id = ppap.id
                avl.status = SupplierAvlStatus.CONDITIONAL if conditional_approval else SupplierAvlStatus.APPROVED
                avl.approved_at = now
                avl.valid_from = now - timedelta(seconds=1)
                avl.valid_until = entry_until
                avl.next_review_at = entry_until
                avl.restrictions = audit.findings if conditional_approval else None
                avl.approved_by = SupplierLifecycleService._operator_id()
        application.status = SupplierQualificationStatus.APPROVED
        application.qualification_level = obj.qualification_level.strip().upper()
        application.decided_at = now
        application.decided_by = SupplierLifecycleService._operator_id()
        application.decision_notes = obj.decision_notes
        application.approved_at = now
        application.valid_until = valid_until
        application.next_review_at = valid_until
        supplier.status = SupplierStatus.ACTIVE
        supplier.cooperation_status = CooperationStatus.NORMAL
        supplier.quality_status = (
            SupplierQualityStatus.CONDITIONAL if conditional_approval else SupplierQualityStatus.QUALIFIED
        )
        supplier.purchasing_enabled = True
        await db.flush()
        return QualificationApplicationDetail.model_validate(application)

    @staticmethod
    async def list_avl(
        db: AsyncSession, supplier_id: int | None = None, material_id: int | None = None,
        status: SupplierAvlStatus | None = None,
    ) -> list[ApprovedMaterialDetail]:
        stmt = select(SupplierApprovedMaterial).where(SupplierApprovedMaterial.deleted == 0)
        if supplier_id is not None:
            stmt = stmt.where(SupplierApprovedMaterial.supplier_id == supplier_id)
        if material_id is not None:
            stmt = stmt.where(SupplierApprovedMaterial.material_id == material_id)
        if status is not None:
            stmt = stmt.where(SupplierApprovedMaterial.status == status)
        rows = (await db.scalars(stmt.order_by(SupplierApprovedMaterial.id.desc()))).all()
        return [ApprovedMaterialDetail.model_validate(row) for row in rows]

    @staticmethod
    async def ensure_supplier_material_approved(db: AsyncSession, supplier_id: int, material_id: int) -> None:
        """Apply AVL enforcement only after a supplier enters the lifecycle workflow."""
        lifecycle_exists = await db.scalar(select(SupplierQualificationApplication.id).where(
            SupplierQualificationApplication.supplier_id == supplier_id,
            SupplierQualificationApplication.deleted == 0,
        ).limit(1))
        if not lifecycle_exists:
            return
        approved_application = await db.scalar(select(SupplierQualificationApplication.id).where(
            SupplierQualificationApplication.supplier_id == supplier_id,
            SupplierQualificationApplication.status == SupplierQualificationStatus.APPROVED,
            SupplierQualificationApplication.deleted == 0,
        ).limit(1))
        if not approved_application:
            raise errors.ConflictError(msg='SUPPLIER_QUALIFICATION_NOT_APPROVED')
        now = timezone.now()
        avl = await db.scalar(select(SupplierApprovedMaterial).where(
            SupplierApprovedMaterial.supplier_id == supplier_id,
            SupplierApprovedMaterial.material_id == material_id,
            SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
            SupplierApprovedMaterial.deleted == 0,
            or_(SupplierApprovedMaterial.valid_from.is_(None), SupplierApprovedMaterial.valid_from <= now),
            or_(SupplierApprovedMaterial.valid_until.is_(None), SupplierApprovedMaterial.valid_until >= now),
        ))
        if not avl:
            raise errors.ConflictError(msg='SUPPLIER_MATERIAL_NOT_IN_AVL')
        ppap = await db.scalar(select(SupplierPpapSubmission).where(
            SupplierPpapSubmission.id == avl.ppap_id,
            SupplierPpapSubmission.status == SupplierPpapStatus.APPROVED,
            SupplierPpapSubmission.deleted == 0,
            or_(SupplierPpapSubmission.expires_at.is_(None), SupplierPpapSubmission.expires_at >= now),
        ))
        if not ppap:
            raise errors.ConflictError(msg='SUPPLIER_MATERIAL_PPAP_EXPIRED')

    @staticmethod
    async def list_reviews(
        db: AsyncSession, supplier_id: int | None = None, status: SupplierReviewStatus | None = None
    ) -> list[PeriodicReviewDetail]:
        stmt = select(SupplierPeriodicReview).where(SupplierPeriodicReview.deleted == 0)
        if supplier_id is not None:
            stmt = stmt.where(SupplierPeriodicReview.supplier_id == supplier_id)
        if status is not None:
            stmt = stmt.where(SupplierPeriodicReview.status == status)
        rows = (await db.scalars(stmt.order_by(SupplierPeriodicReview.id.desc()))).all()
        return [PeriodicReviewDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_review(
        db: AsyncSession, avl_id: int, obj: CreatePeriodicReview
    ) -> PeriodicReviewDetail:
        avl = await db.scalar(select(SupplierApprovedMaterial).where(
            SupplierApprovedMaterial.id == avl_id, SupplierApprovedMaterial.deleted == 0
        ).with_for_update())
        if not avl:
            raise errors.NotFoundError(msg='SUPPLIER_AVL_NOT_FOUND')
        existing = await db.scalar(select(SupplierPeriodicReview.id).where(
            SupplierPeriodicReview.avl_id == avl.id,
            SupplierPeriodicReview.status == SupplierReviewStatus.PLANNED,
            SupplierPeriodicReview.deleted == 0,
        ))
        if existing:
            raise errors.ConflictError(msg='SUPPLIER_AVL_REVIEW_ALREADY_PLANNED')
        assessment = await db.scalar(select(SupplierQualityAssessment).where(
            SupplierQualityAssessment.supplier_id == avl.supplier_id,
            SupplierQualityAssessment.deleted == 0,
        ).order_by(SupplierQualityAssessment.assessed_at.desc(), SupplierQualityAssessment.id.desc()))
        row = SupplierPeriodicReview(
            review_no=SupplierLifecycleService._number('SRV'), supplier_id=avl.supplier_id,
            avl_id=avl.id, planned_at=obj.planned_at or avl.next_review_at or timezone.now(),
            quality_assessment_id=assessment.id if assessment else None,
            score_snapshot=assessment.overall_score if assessment else None,
        )
        db.add(row)
        await db.flush()
        return PeriodicReviewDetail.model_validate(row)

    @staticmethod
    async def generate_due_reviews(db: AsyncSession) -> list[PeriodicReviewDetail]:
        now = timezone.now()
        avls = (await db.scalars(select(SupplierApprovedMaterial).where(
            SupplierApprovedMaterial.deleted == 0,
            SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
            SupplierApprovedMaterial.next_review_at <= now,
        ))).all()
        created: list[PeriodicReviewDetail] = []
        for avl in avls:
            exists = await db.scalar(select(SupplierPeriodicReview.id).where(
                SupplierPeriodicReview.avl_id == avl.id,
                SupplierPeriodicReview.status == SupplierReviewStatus.PLANNED,
                SupplierPeriodicReview.deleted == 0,
            ))
            if not exists:
                created.append(await SupplierLifecycleService.create_review(db, avl.id, CreatePeriodicReview()))
        return created

    @staticmethod
    async def complete_review(
        db: AsyncSession, review_id: int, obj: CompletePeriodicReview
    ) -> PeriodicReviewDetail:
        review = await db.scalar(select(SupplierPeriodicReview).where(
            SupplierPeriodicReview.id == review_id, SupplierPeriodicReview.deleted == 0
        ).with_for_update())
        if not review:
            raise errors.NotFoundError(msg='SUPPLIER_REVIEW_NOT_FOUND')
        if review.status != SupplierReviewStatus.PLANNED:
            raise errors.ConflictError(msg='SUPPLIER_REVIEW_NOT_PLANNED')
        avl = await db.scalar(select(SupplierApprovedMaterial).where(
            SupplierApprovedMaterial.id == review.avl_id, SupplierApprovedMaterial.deleted == 0
        ).with_for_update())
        if not avl:
            raise errors.NotFoundError(msg='SUPPLIER_AVL_NOT_FOUND')
        relation = await db.scalar(select(SupplierMaterial).where(
            SupplierMaterial.id == avl.supplier_material_id, SupplierMaterial.deleted == 0
        ).with_for_update())
        supplier = await SupplierLifecycleService._supplier(db, review.supplier_id, lock=True)
        now = timezone.now()
        review.status = SupplierReviewStatus.COMPLETED
        review.decision = obj.decision
        review.reviewed_at = now
        review.reviewed_by = SupplierLifecycleService._operator_id()
        review.notes = obj.notes
        avl.last_review_at = now
        if obj.decision in (SupplierReviewDecision.CONTINUE, SupplierReviewDecision.CONDITIONAL):
            next_review = now + timedelta(days=obj.next_review_days)
            review.next_review_at = next_review
            avl.next_review_at = next_review
            avl.valid_until = next_review
            avl.status = (
                SupplierAvlStatus.APPROVED
                if obj.decision == SupplierReviewDecision.CONTINUE else SupplierAvlStatus.CONDITIONAL
            )
            if relation:
                relation.status = SupplierMaterialStatus.ACTIVE
                relation.quality_inspection_required = True
            supplier.purchasing_enabled = True
            supplier.cooperation_status = CooperationStatus.NORMAL
            supplier.quality_status = (
                SupplierQualityStatus.QUALIFIED
                if obj.decision == SupplierReviewDecision.CONTINUE else SupplierQualityStatus.CONDITIONAL
            )
            application = await db.scalar(select(SupplierQualificationApplication).where(
                SupplierQualificationApplication.id == avl.qualification_id,
                SupplierQualificationApplication.deleted == 0,
            ).with_for_update())
            if application:
                application.valid_until = next_review
                application.next_review_at = next_review
        else:
            avl.status = (
                SupplierAvlStatus.SUSPENDED
                if obj.decision == SupplierReviewDecision.SUSPEND else SupplierAvlStatus.REMOVED
            )
            if relation:
                relation.status = (
                    SupplierMaterialStatus.SUSPENDED
                    if obj.decision == SupplierReviewDecision.SUSPEND else SupplierMaterialStatus.DISABLED
                )
            await db.flush()
            usable_count = int(await db.scalar(select(func.count(SupplierApprovedMaterial.id)).where(
                SupplierApprovedMaterial.supplier_id == supplier.id,
                SupplierApprovedMaterial.status.in_((SupplierAvlStatus.APPROVED, SupplierAvlStatus.CONDITIONAL)),
                SupplierApprovedMaterial.deleted == 0,
            )) or 0)
            if usable_count == 0:
                supplier.purchasing_enabled = False
                supplier.cooperation_status = CooperationStatus.SUSPENDED
                supplier.quality_status = SupplierQualityStatus.UNQUALIFIED
                applications = (await db.scalars(select(SupplierQualificationApplication).where(
                    SupplierQualificationApplication.supplier_id == supplier.id,
                    SupplierQualificationApplication.status == SupplierQualificationStatus.APPROVED,
                    SupplierQualificationApplication.deleted == 0,
                ))).all()
                for application in applications:
                    application.status = (
                        SupplierQualificationStatus.SUSPENDED
                        if obj.decision == SupplierReviewDecision.SUSPEND else SupplierQualificationStatus.REMOVED
                    )
        await db.flush()
        return PeriodicReviewDetail.model_validate(review)


supplier_lifecycle_service = SupplierLifecycleService()
