from collections import Counter
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.purchasing.enums import PurchaseDeliveryPerformanceStatus
from backend.plugin.purchasing.model import PurchaseOrderDeliveryPerformance, SupplierReceipt
from backend.plugin.quality.enums import (
    InspectionResult,
    InspectionStatus,
    InspectionType,
    DispositionType,
    SupplierCorrectiveActionStatus,
    SupplierCorrectiveVerificationResult,
    SupplierProcurementDecision,
    SupplierQualityGrade,
    SupplierQualityPolicyStatus,
)
from backend.plugin.quality.model import NonconformanceDisposition, NonconformanceReport, QualityInspection
from backend.plugin.quality.model.sqm import (
    SupplierCorrectiveAction,
    SupplierQualityAssessment,
    SupplierQualityPolicy,
)
from backend.plugin.quality.schema.quality import CreateDisposition, CreateInspection
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
from backend.plugin.supplier.enums import SupplierQualityStatus
from backend.plugin.supplier.model import Supplier, SupplierMaterial
from backend.utils.timezone import timezone


ACTIVE_SCAR_STATUSES = (
    SupplierCorrectiveActionStatus.ISSUED,
    SupplierCorrectiveActionStatus.RESPONDED,
    SupplierCorrectiveActionStatus.RETEST_PENDING,
    SupplierCorrectiveActionStatus.REJECTED,
)
SCORE_QUANTUM = Decimal('0.01')


class SupplierQualityManagementService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _percent(numerator: Decimal | int, denominator: Decimal | int) -> Decimal:
        denominator = Decimal(denominator)
        if denominator <= 0:
            return Decimal('0')
        return (Decimal(numerator) / denominator * Decimal('100')).quantize(
            SCORE_QUANTUM, rounding=ROUND_HALF_UP
        )

    @staticmethod
    async def get_policy(
        db: AsyncSession, supplier_id: int, *, create_default: bool = False, lock: bool = False
    ) -> SupplierQualityPolicy | None:
        statement = select(SupplierQualityPolicy).where(
            SupplierQualityPolicy.supplier_id == supplier_id,
            SupplierQualityPolicy.deleted == 0,
        )
        if lock:
            statement = statement.with_for_update()
        policy = await db.scalar(statement)
        if policy is None and create_default:
            supplier = await db.scalar(select(Supplier).where(
                Supplier.id == supplier_id, Supplier.deleted == 0
            ))
            if not supplier:
                raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
            policy = SupplierQualityPolicy(supplier_id=supplier_id)
            db.add(policy)
            await db.flush()
        return policy

    @staticmethod
    async def list_policies(db: AsyncSession) -> list[SupplierQualityPolicyDetail]:
        rows = (await db.scalars(select(SupplierQualityPolicy).where(
            SupplierQualityPolicy.deleted == 0
        ).order_by(SupplierQualityPolicy.supplier_id))).all()
        return [SupplierQualityPolicyDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_policy(
        db: AsyncSession, supplier_id: int, obj: SupplierQualityPolicyUpsert
    ) -> SupplierQualityPolicyDetail:
        policy = await SupplierQualityManagementService.get_policy(
            db, supplier_id, create_default=True, lock=True
        )
        for key, value in obj.model_dump().items():
            setattr(policy, key, value)
        await db.flush()
        return SupplierQualityPolicyDetail.model_validate(policy)

    @staticmethod
    async def ensure_scar_for_ncr(
        db: AsyncSession, ncr: NonconformanceReport
    ) -> SupplierCorrectiveAction | None:
        inspection = await db.scalar(select(QualityInspection).where(
            QualityInspection.id == ncr.inspection_id,
            QualityInspection.deleted == 0,
        ))
        if (
            not inspection
            or inspection.inspection_type != InspectionType.INCOMING
            or inspection.source_type != 'SUPPLIER_RECEIPT'
            or not inspection.source_id
        ):
            return None
        receipt = await db.scalar(select(SupplierReceipt).where(
            SupplierReceipt.id == inspection.source_id,
            SupplierReceipt.deleted == 0,
        ))
        if not receipt:
            raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_NOT_FOUND')
        existing = await db.scalar(select(SupplierCorrectiveAction).where(
            SupplierCorrectiveAction.ncr_id == ncr.id,
            SupplierCorrectiveAction.deleted == 0,
        ).with_for_update())
        if existing:
            return existing
        scar = SupplierCorrectiveAction(
            scar_no=f'SCAR-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            supplier_id=receipt.supplier_id,
            ncr_id=ncr.id,
            inspection_id=inspection.id,
            supplier_receipt_id=receipt.id,
            material_id=ncr.material_id,
            nonconforming_quantity=ncr.nonconforming_quantity,
            defect_description=ncr.defect_description,
            severity=ncr.severity.upper(),
        )
        db.add(scar)
        await db.flush()
        return scar

    @staticmethod
    async def list_scars(
        db: AsyncSession, supplier_id: int | None = None, status: str | None = None
    ) -> list[SupplierCorrectiveActionDetail]:
        statement = select(SupplierCorrectiveAction).where(SupplierCorrectiveAction.deleted == 0)
        if supplier_id:
            statement = statement.where(SupplierCorrectiveAction.supplier_id == supplier_id)
        if status:
            statement = statement.where(SupplierCorrectiveAction.status == status)
        rows = (await db.scalars(statement.order_by(
            SupplierCorrectiveAction.created_time.desc(), SupplierCorrectiveAction.id.desc()
        ))).all()
        return [SupplierCorrectiveActionDetail.model_validate(row) for row in rows]

    @staticmethod
    async def _get_scar(
        db: AsyncSession, scar_id: int, *, lock: bool = False
    ) -> SupplierCorrectiveAction:
        statement = select(SupplierCorrectiveAction).where(
            SupplierCorrectiveAction.id == scar_id,
            SupplierCorrectiveAction.deleted == 0,
        )
        if lock:
            statement = statement.with_for_update()
        scar = await db.scalar(statement)
        if not scar:
            raise errors.NotFoundError(msg='SUPPLIER_SCAR_NOT_FOUND')
        return scar

    @staticmethod
    async def issue_scar(
        db: AsyncSession, scar_id: int, obj: IssueSupplierCorrectiveAction
    ) -> SupplierCorrectiveActionDetail:
        scar = await SupplierQualityManagementService._get_scar(db, scar_id, lock=True)
        if scar.status == SupplierCorrectiveActionStatus.ISSUED:
            return SupplierCorrectiveActionDetail.model_validate(scar)
        if scar.status != SupplierCorrectiveActionStatus.DRAFT:
            raise errors.ConflictError(msg='SUPPLIER_SCAR_NOT_DRAFT')
        now = timezone.now()
        scar.status = SupplierCorrectiveActionStatus.ISSUED
        scar.issued_at = now
        scar.due_at = obj.due_at or now + timedelta(days=14)
        await db.flush()
        return SupplierCorrectiveActionDetail.model_validate(scar)

    @staticmethod
    async def respond_scar(
        db: AsyncSession, scar_id: int, obj: RespondSupplierCorrectiveAction
    ) -> SupplierCorrectiveActionDetail:
        scar = await SupplierQualityManagementService._get_scar(db, scar_id, lock=True)
        if scar.status not in (
            SupplierCorrectiveActionStatus.ISSUED,
            SupplierCorrectiveActionStatus.REJECTED,
        ):
            raise errors.ConflictError(msg='SUPPLIER_SCAR_NOT_RESPONDABLE')
        for key, value in obj.model_dump().items():
            setattr(scar, key, value)
        scar.status = SupplierCorrectiveActionStatus.RESPONDED
        scar.responded_at = timezone.now()
        scar.verification_result = None
        scar.verification_notes = None
        scar.verified_at = None
        await db.flush()
        return SupplierCorrectiveActionDetail.model_validate(scar)

    @staticmethod
    async def create_reinspection(
        db: AsyncSession, scar_id: int
    ) -> SupplierCorrectiveActionDetail:
        scar = await SupplierQualityManagementService._get_scar(db, scar_id, lock=True)
        if scar.status == SupplierCorrectiveActionStatus.RETEST_PENDING and scar.reinspection_id:
            return SupplierCorrectiveActionDetail.model_validate(scar)
        if scar.status != SupplierCorrectiveActionStatus.RESPONDED:
            raise errors.ConflictError(msg='SUPPLIER_SCAR_NOT_READY_FOR_RETEST')
        from backend.plugin.quality.service.quality_service import quality_service
        ncr = await db.scalar(select(NonconformanceReport).where(
            NonconformanceReport.id == scar.ncr_id,
            NonconformanceReport.deleted == 0,
        ))
        if not ncr:
            raise errors.NotFoundError(msg='NCR_NOT_FOUND')
        if scar.disposition_id is None:
            disposition = await quality_service.create_disposition(db, CreateDisposition(
                ncr_id=ncr.id,
                disposition_type=DispositionType.REINSPECT,
                quantity=scar.nonconforming_quantity,
                decision_reason=f'供应商 {scar.scar_no} 整改后复验',
            ))
            disposition = await quality_service.execute_disposition(db, disposition.id)
            scar.disposition_id = disposition.id
            inspection = await quality_service.get_inspection(db, disposition.reinspection_id)
        else:
            disposition = await db.scalar(select(NonconformanceDisposition).where(
                NonconformanceDisposition.id == scar.disposition_id,
                NonconformanceDisposition.deleted == 0,
            ).with_for_update())
            if not disposition:
                raise errors.NotFoundError(msg='MRB_DISPOSITION_NOT_FOUND')
            inspection = await quality_service.create_inspection(db, CreateInspection(
                inspection_type=InspectionType.RETEST,
                material_id=scar.material_id,
                lot_id=ncr.lot_id,
                parent_inspection_id=scar.reinspection_id or scar.inspection_id,
                source_type='NCR',
                source_id=ncr.id,
                source_no=ncr.ncr_no,
                sample_quantity=scar.nonconforming_quantity,
            ))
            disposition.reinspection_id = inspection.id
        scar.reinspection_id = inspection.id
        scar.status = SupplierCorrectiveActionStatus.RETEST_PENDING
        await db.flush()
        return SupplierCorrectiveActionDetail.model_validate(scar)

    @staticmethod
    async def verify_scar(
        db: AsyncSession, scar_id: int, obj: VerifySupplierCorrectiveAction
    ) -> SupplierCorrectiveActionDetail:
        scar = await SupplierQualityManagementService._get_scar(db, scar_id, lock=True)
        if scar.status != SupplierCorrectiveActionStatus.RETEST_PENDING or not scar.reinspection_id:
            raise errors.ConflictError(msg='SUPPLIER_SCAR_NOT_VERIFIABLE')
        inspection = await db.scalar(select(QualityInspection).where(
            QualityInspection.id == scar.reinspection_id,
            QualityInspection.deleted == 0,
        ))
        if not inspection or inspection.status != InspectionStatus.COMPLETED:
            raise errors.ConflictError(msg='SUPPLIER_SCAR_RETEST_NOT_COMPLETED')
        now = timezone.now()
        passed = inspection.result == InspectionResult.PASS
        scar.verification_result = (
            SupplierCorrectiveVerificationResult.PASS
            if passed else SupplierCorrectiveVerificationResult.FAIL
        )
        scar.verification_notes = obj.verification_notes
        scar.verified_at = now
        scar.verified_by = SupplierQualityManagementService._operator_id()
        scar.status = (
            SupplierCorrectiveActionStatus.CLOSED if passed
            else SupplierCorrectiveActionStatus.REJECTED
        )
        scar.closed_at = now if passed else None
        await db.flush()
        await SupplierQualityManagementService.assess_supplier(db, scar.supplier_id)
        return SupplierCorrectiveActionDetail.model_validate(scar)

    @staticmethod
    async def list_assessments(
        db: AsyncSession, supplier_id: int | None = None, limit: int = 200
    ) -> list[SupplierQualityAssessmentDetail]:
        statement = select(SupplierQualityAssessment).where(
            SupplierQualityAssessment.deleted == 0
        )
        if supplier_id:
            statement = statement.where(SupplierQualityAssessment.supplier_id == supplier_id)
        rows = (await db.scalars(statement.order_by(
            SupplierQualityAssessment.assessed_at.desc(), SupplierQualityAssessment.id.desc()
        ).limit(limit))).all()
        return [SupplierQualityAssessmentDetail.model_validate(row) for row in rows]

    @staticmethod
    async def assess_supplier(
        db: AsyncSession, supplier_id: int
    ) -> SupplierQualityAssessmentDetail:
        supplier = await db.scalar(select(Supplier).where(
            Supplier.id == supplier_id, Supplier.deleted == 0
        ).with_for_update())
        if not supplier:
            raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
        policy = await SupplierQualityManagementService.get_policy(
            db, supplier_id, create_default=True
        )
        now = timezone.now()
        start = now - timedelta(days=policy.rolling_days)
        inspections = (await db.scalars(
            select(QualityInspection)
            .join(SupplierReceipt, SupplierReceipt.id == QualityInspection.source_id)
            .where(
                QualityInspection.inspection_type == InspectionType.INCOMING,
                QualityInspection.source_type == 'SUPPLIER_RECEIPT',
                QualityInspection.status == InspectionStatus.COMPLETED,
                QualityInspection.inspected_at >= start,
                QualityInspection.deleted == 0,
                SupplierReceipt.supplier_id == supplier_id,
                SupplierReceipt.deleted == 0,
            )
        )).all()
        scars = (await db.scalars(select(SupplierCorrectiveAction).where(
            SupplierCorrectiveAction.supplier_id == supplier_id,
            SupplierCorrectiveAction.created_time >= start,
            SupplierCorrectiveAction.deleted == 0,
        ))).all()
        deliveries = (await db.scalars(select(PurchaseOrderDeliveryPerformance).where(
            PurchaseOrderDeliveryPerformance.supplier_id == supplier_id,
            PurchaseOrderDeliveryPerformance.assessed_at >= start,
            PurchaseOrderDeliveryPerformance.deleted == 0,
        ))).all()

        inspection_count = len(inspections)
        passed_count = sum(row.result == InspectionResult.PASS for row in inspections)
        failed_count = inspection_count - passed_count
        inspected_quantity = sum((row.sample_quantity for row in inspections), Decimal('0'))
        rejected_quantity = sum((row.rejected_quantity for row in inspections), Decimal('0'))
        pass_rate = SupplierQualityManagementService._percent(passed_count, inspection_count)
        acceptance_rate = SupplierQualityManagementService._percent(
            inspected_quantity - rejected_quantity, inspected_quantity
        )
        scar_count = len(scars)
        scar_closed_count = sum(
            row.status == SupplierCorrectiveActionStatus.CLOSED
            and row.verification_result == SupplierCorrectiveVerificationResult.PASS
            for row in scars
        )
        scar_on_time_count = sum(
            row.status == SupplierCorrectiveActionStatus.CLOSED
            and row.closed_at is not None
            and (row.due_at is None or row.closed_at <= row.due_at)
            for row in scars
        )
        if scar_count:
            effective_rate = SupplierQualityManagementService._percent(scar_closed_count, scar_count)
            on_time_rate = SupplierQualityManagementService._percent(scar_on_time_count, scar_count)
            corrective_score = (
                effective_rate * Decimal('0.70') + on_time_rate * Decimal('0.30')
            ).quantize(SCORE_QUANTUM)
        else:
            corrective_score = Decimal('100')
        incoming_score = (
            pass_rate * Decimal('0.60') + acceptance_rate * Decimal('0.40')
        ).quantize(SCORE_QUANTUM)
        quality_score = (
            incoming_score * Decimal('0.80') + corrective_score * Decimal('0.20')
        ).quantize(SCORE_QUANTUM)
        delivery_line_count = len(deliveries)
        otif_line_count = sum(
            row.otif_status == PurchaseDeliveryPerformanceStatus.OTIF for row in deliveries
        )
        delivery_score = (
            SupplierQualityManagementService._percent(otif_line_count, delivery_line_count)
            if delivery_line_count else Decimal('100')
        )
        overall_score = (
            quality_score * policy.quality_weight / Decimal('100')
            + delivery_score * policy.delivery_weight / Decimal('100')
        ).quantize(SCORE_QUANTUM)
        critical_open = any(
            row.severity == 'CRITICAL' and row.status in ACTIVE_SCAR_STATUSES for row in scars
        )
        if inspection_count < policy.minimum_inspections:
            grade = SupplierQualityGrade.UNRATED
            decision = SupplierProcurementDecision.PENDING
        elif critical_open and policy.block_on_open_critical_scar:
            grade = SupplierQualityGrade.D
            decision = SupplierProcurementDecision.SUSPENDED
        elif overall_score >= policy.excellent_score:
            grade = SupplierQualityGrade.A
            decision = SupplierProcurementDecision.APPROVED
        elif overall_score >= policy.qualified_score:
            grade = SupplierQualityGrade.B
            decision = SupplierProcurementDecision.APPROVED
        elif overall_score >= policy.conditional_score:
            grade = SupplierQualityGrade.C
            decision = SupplierProcurementDecision.CONDITIONAL
        else:
            grade = SupplierQualityGrade.D
            decision = SupplierProcurementDecision.SUSPENDED

        assessment = SupplierQualityAssessment(
            assessment_no=f'SQA-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            supplier_id=supplier_id,
            policy_id=policy.id,
            period_start=start,
            period_end=now,
            assessed_at=now,
            grade=grade,
            procurement_decision=decision,
            overall_score=overall_score,
            inspection_count=inspection_count,
            passed_count=passed_count,
            failed_count=failed_count,
            inspected_quantity=inspected_quantity,
            rejected_quantity=rejected_quantity,
            pass_rate=pass_rate,
            acceptance_rate=acceptance_rate,
            scar_count=scar_count,
            scar_closed_count=scar_closed_count,
            scar_on_time_count=scar_on_time_count,
            corrective_score=corrective_score,
            quality_score=quality_score,
            delivery_line_count=delivery_line_count,
            otif_line_count=otif_line_count,
            delivery_score=delivery_score,
            critical_scar_open=critical_open,
        )
        db.add(assessment)
        await db.flush()
        if policy.auto_apply:
            materials = (await db.scalars(select(SupplierMaterial).where(
                SupplierMaterial.supplier_id == supplier_id,
                SupplierMaterial.deleted == 0,
            ).with_for_update())).all()
            if decision == SupplierProcurementDecision.APPROVED:
                supplier.quality_status = SupplierQualityStatus.QUALIFIED
                supplier.preferred = grade == SupplierQualityGrade.A
            elif decision == SupplierProcurementDecision.CONDITIONAL:
                supplier.quality_status = SupplierQualityStatus.CONDITIONAL
                supplier.preferred = False
                for relation in materials:
                    relation.quality_inspection_required = True
            elif decision == SupplierProcurementDecision.SUSPENDED:
                supplier.quality_status = SupplierQualityStatus.UNQUALIFIED
                supplier.preferred = False
                for relation in materials:
                    relation.quality_inspection_required = True
            else:
                supplier.quality_status = SupplierQualityStatus.PENDING
            assessment.applied_at = now
            assessment.applied_notes = f'自动应用 SQM {grade.value} 级采购策略'
        await db.flush()
        return SupplierQualityAssessmentDetail.model_validate(assessment)

    @staticmethod
    async def assess_all(db: AsyncSession) -> list[SupplierQualityAssessmentDetail]:
        supplier_ids = (await db.scalars(select(Supplier.id).where(
            Supplier.deleted == 0
        ).order_by(Supplier.id))).all()
        return [
            await SupplierQualityManagementService.assess_supplier(db, supplier_id)
            for supplier_id in supplier_ids
        ]

    @staticmethod
    async def assess_supplier_by_inspection(
        db: AsyncSession, inspection: QualityInspection
    ) -> SupplierQualityAssessmentDetail | None:
        if inspection.source_type != 'SUPPLIER_RECEIPT' or not inspection.source_id:
            return None
        receipt = await db.scalar(select(SupplierReceipt).where(
            SupplierReceipt.id == inspection.source_id,
            SupplierReceipt.deleted == 0,
        ))
        return (
            await SupplierQualityManagementService.assess_supplier(db, receipt.supplier_id)
            if receipt else None
        )

    @staticmethod
    async def ensure_supplier_purchasable(db: AsyncSession, supplier_id: int) -> None:
        supplier = await db.scalar(select(Supplier).where(
            Supplier.id == supplier_id, Supplier.deleted == 0
        ))
        if supplier and supplier.quality_status == SupplierQualityStatus.UNQUALIFIED:
            raise errors.ConflictError(msg='SUPPLIER_SQM_SUSPENDED')
        latest = await db.scalar(select(SupplierQualityAssessment).where(
            SupplierQualityAssessment.supplier_id == supplier_id,
            SupplierQualityAssessment.deleted == 0,
        ).order_by(
            SupplierQualityAssessment.assessed_at.desc(), SupplierQualityAssessment.id.desc()
        ).limit(1))
        if latest and latest.procurement_decision == SupplierProcurementDecision.SUSPENDED:
            raise errors.ConflictError(msg='SUPPLIER_SQM_SUSPENDED')
        policy = await SupplierQualityManagementService.get_policy(db, supplier_id)
        if policy and policy.status == SupplierQualityPolicyStatus.ACTIVE and policy.block_on_open_critical_scar:
            critical = await db.scalar(select(SupplierCorrectiveAction.id).where(
                SupplierCorrectiveAction.supplier_id == supplier_id,
                SupplierCorrectiveAction.severity == 'CRITICAL',
                SupplierCorrectiveAction.status.in_(ACTIVE_SCAR_STATUSES),
                SupplierCorrectiveAction.deleted == 0,
            ).limit(1))
            if critical:
                raise errors.ConflictError(msg='SUPPLIER_CRITICAL_SCAR_OPEN')

    @staticmethod
    async def dashboard(db: AsyncSession) -> SupplierQualityDashboard:
        scars = (await db.scalars(select(SupplierCorrectiveAction).where(
            SupplierCorrectiveAction.deleted == 0
        ))).all()
        latest_by_supplier: dict[int, SupplierQualityAssessment] = {}
        assessments = (await db.scalars(select(SupplierQualityAssessment).where(
            SupplierQualityAssessment.deleted == 0
        ).order_by(
            SupplierQualityAssessment.assessed_at.desc(), SupplierQualityAssessment.id.desc()
        ))).all()
        for assessment in assessments:
            latest_by_supplier.setdefault(assessment.supplier_id, assessment)
        grade_counts = Counter(row.grade.value for row in latest_by_supplier.values())
        now = timezone.now()
        return SupplierQualityDashboard(
            open_scar_count=sum(row.status in ACTIVE_SCAR_STATUSES for row in scars),
            overdue_scar_count=sum(
                row.status in ACTIVE_SCAR_STATUSES and row.due_at is not None and row.due_at < now
                for row in scars
            ),
            retest_pending_count=sum(
                row.status == SupplierCorrectiveActionStatus.RETEST_PENDING for row in scars
            ),
            suspended_supplier_count=sum(
                row.procurement_decision == SupplierProcurementDecision.SUSPENDED
                for row in latest_by_supplier.values()
            ),
            conditional_supplier_count=sum(
                row.procurement_decision == SupplierProcurementDecision.CONDITIONAL
                for row in latest_by_supplier.values()
            ),
            grade_counts=dict(grade_counts),
        )


sqm_service = SupplierQualityManagementService()
