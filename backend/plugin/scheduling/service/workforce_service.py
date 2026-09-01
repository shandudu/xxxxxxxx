from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.app.admin.model import User
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.routing.model import Operation, WorkCenter
from backend.plugin.scheduling.enums import ConfigStatus, QualificationStatus, RosterStatus
from backend.plugin.scheduling.model import (
    JobType,
    PositionQualificationRule,
    Shift,
    SkillLevel,
    WorkerAuthorization,
    WorkerCertificate,
    WorkerRoster,
    WorkerSkill,
)
from backend.plugin.scheduling.schema.workforce import (
    AccessCheckResult,
    JobTypeDetail,
    JobTypeInput,
    PositionRuleDetail,
    PositionRuleInput,
    SkillLevelDetail,
    SkillLevelInput,
    WorkerAuthorizationDetail,
    WorkerAuthorizationInput,
    WorkerCertificateDetail,
    WorkerCertificateInput,
    WorkforceDashboard,
    WorkerRosterDetail,
    WorkerRosterInput,
    WorkerSkillDetail,
    WorkerSkillInput,
)
from backend.utils.timezone import timezone


class WorkforceService:
    @staticmethod
    def operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _active_ref(db: AsyncSession, model, row_id: int, error: str):
        row = await db.scalar(select(model).where(model.id == row_id, model.deleted == 0))
        if not row or getattr(row, 'status', ConfigStatus.ACTIVE) not in (
            ConfigStatus.ACTIVE,
            QualificationStatus.ACTIVE,
        ):
            raise errors.ConflictError(msg=error)
        return row

    @staticmethod
    async def _user(db: AsyncSession, user_id: int) -> User:
        row = await db.scalar(select(User).where(User.id == user_id, User.deleted == 0, User.status == 1))
        if not row:
            raise errors.ConflictError(msg='WORKFORCE_USER_NOT_ACTIVE')
        return row

    @staticmethod
    async def list_job_types(db: AsyncSession) -> list[JobTypeDetail]:
        rows = (await db.scalars(select(JobType).where(JobType.deleted == 0).order_by(JobType.job_code))).all()
        return [JobTypeDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_job_type(db: AsyncSession, obj: JobTypeInput) -> JobTypeDetail:
        row = await db.scalar(select(JobType).where(JobType.job_code == obj.job_code, JobType.deleted == 0).with_for_update())
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = JobType(**obj.model_dump())
            db.add(row)
        await db.flush()
        return JobTypeDetail.model_validate(row)

    @staticmethod
    async def list_skill_levels(db: AsyncSession) -> list[SkillLevelDetail]:
        rows = (await db.scalars(select(SkillLevel).where(SkillLevel.deleted == 0).order_by(SkillLevel.rank_order))).all()
        return [SkillLevelDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_skill_level(db: AsyncSession, obj: SkillLevelInput) -> SkillLevelDetail:
        duplicate_rank = await db.scalar(select(SkillLevel.id).where(SkillLevel.rank_order == obj.rank_order, SkillLevel.level_code != obj.level_code, SkillLevel.deleted == 0))
        if duplicate_rank:
            raise errors.ConflictError(msg='SKILL_LEVEL_RANK_EXISTS')
        row = await db.scalar(select(SkillLevel).where(SkillLevel.level_code == obj.level_code, SkillLevel.deleted == 0).with_for_update())
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = SkillLevel(**obj.model_dump())
            db.add(row)
        await db.flush()
        return SkillLevelDetail.model_validate(row)

    @staticmethod
    async def list_skills(db: AsyncSession, user_id: int | None = None) -> list[WorkerSkillDetail]:
        stmt = select(WorkerSkill).where(WorkerSkill.deleted == 0)
        if user_id:
            stmt = stmt.where(WorkerSkill.user_id == user_id)
        rows = (await db.scalars(stmt.order_by(WorkerSkill.user_id, WorkerSkill.job_type_id))).all()
        return [WorkerSkillDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_skill(db: AsyncSession, obj: WorkerSkillInput) -> WorkerSkillDetail:
        await WorkforceService._user(db, obj.user_id)
        await WorkforceService._active_ref(db, JobType, obj.job_type_id, 'JOB_TYPE_NOT_ACTIVE')
        await WorkforceService._active_ref(db, SkillLevel, obj.skill_level_id, 'SKILL_LEVEL_NOT_ACTIVE')
        row = await db.scalar(select(WorkerSkill).where(WorkerSkill.user_id == obj.user_id, WorkerSkill.job_type_id == obj.job_type_id, WorkerSkill.deleted == 0).with_for_update())
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = WorkerSkill(**obj.model_dump())
            db.add(row)
        await db.flush()
        return WorkerSkillDetail.model_validate(row)

    @staticmethod
    def _certificate_detail(row: WorkerCertificate) -> WorkerCertificateDetail:
        result = WorkerCertificateDetail.model_validate(row)
        today = timezone.now().date()
        result.validity_state = 'REVOKED' if row.status != QualificationStatus.ACTIVE else ('NOT_YET_VALID' if row.valid_from > today else ('EXPIRED' if row.expires_on < today else ('EXPIRING' if row.expires_on <= today + timedelta(days=30) else 'VALID')))
        return result

    @staticmethod
    async def list_certificates(db: AsyncSession, user_id: int | None = None) -> list[WorkerCertificateDetail]:
        stmt = select(WorkerCertificate).where(WorkerCertificate.deleted == 0)
        if user_id:
            stmt = stmt.where(WorkerCertificate.user_id == user_id)
        rows = (await db.scalars(stmt.order_by(WorkerCertificate.expires_on, WorkerCertificate.user_id))).all()
        return [WorkforceService._certificate_detail(row) for row in rows]

    @staticmethod
    async def upsert_certificate(db: AsyncSession, obj: WorkerCertificateInput) -> WorkerCertificateDetail:
        await WorkforceService._user(db, obj.user_id)
        row = await db.scalar(select(WorkerCertificate).where(WorkerCertificate.certificate_no == obj.certificate_no, WorkerCertificate.deleted == 0).with_for_update())
        if row and row.user_id != obj.user_id:
            raise errors.ConflictError(msg='CERTIFICATE_NUMBER_OWNED_BY_OTHER_USER')
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = WorkerCertificate(**obj.model_dump())
            db.add(row)
        await db.flush()
        return WorkforceService._certificate_detail(row)

    @staticmethod
    async def list_rules(db: AsyncSession) -> list[PositionRuleDetail]:
        rows = (await db.scalars(select(PositionQualificationRule).where(PositionQualificationRule.deleted == 0).order_by(PositionQualificationRule.rule_code))).all()
        return [PositionRuleDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_rule(db: AsyncSession, obj: PositionRuleInput) -> PositionRuleDetail:
        await WorkforceService._active_ref(db, JobType, obj.job_type_id, 'JOB_TYPE_NOT_ACTIVE')
        await WorkforceService._active_ref(db, SkillLevel, obj.minimum_skill_level_id, 'SKILL_LEVEL_NOT_ACTIVE')
        if obj.operation_id and not await db.scalar(select(Operation.id).where(Operation.id == obj.operation_id, Operation.deleted == 0)):
            raise errors.ConflictError(msg='OPERATION_NOT_FOUND')
        if obj.work_center_id and not await db.scalar(select(WorkCenter.id).where(WorkCenter.id == obj.work_center_id, WorkCenter.deleted == 0)):
            raise errors.ConflictError(msg='WORK_CENTER_NOT_FOUND')
        row = await db.scalar(select(PositionQualificationRule).where(PositionQualificationRule.rule_code == obj.rule_code, PositionQualificationRule.deleted == 0).with_for_update())
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = PositionQualificationRule(**obj.model_dump())
            db.add(row)
        await db.flush()
        return PositionRuleDetail.model_validate(row)

    @staticmethod
    async def list_authorizations(db: AsyncSession, user_id: int | None = None) -> list[WorkerAuthorizationDetail]:
        stmt = select(WorkerAuthorization).where(WorkerAuthorization.deleted == 0)
        if user_id:
            stmt = stmt.where(WorkerAuthorization.user_id == user_id)
        rows = (await db.scalars(stmt.order_by(WorkerAuthorization.effective_from.desc()))).all()
        return [WorkerAuthorizationDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_authorization(db: AsyncSession, obj: WorkerAuthorizationInput) -> WorkerAuthorizationDetail:
        await WorkforceService._user(db, obj.user_id)
        await WorkforceService._active_ref(db, JobType, obj.job_type_id, 'JOB_TYPE_NOT_ACTIVE')
        await WorkforceService._active_ref(db, WorkCenter, obj.work_center_id, 'WORK_CENTER_NOT_ACTIVE')
        if obj.operation_id and not await db.scalar(select(Operation.id).where(Operation.id == obj.operation_id, Operation.deleted == 0)):
            raise errors.ConflictError(msg='OPERATION_NOT_FOUND')
        stmt = select(WorkerAuthorization).where(
            WorkerAuthorization.user_id == obj.user_id,
            WorkerAuthorization.job_type_id == obj.job_type_id,
            WorkerAuthorization.work_center_id == obj.work_center_id,
            WorkerAuthorization.deleted == 0,
            WorkerAuthorization.operation_id == obj.operation_id if obj.operation_id else WorkerAuthorization.operation_id.is_(None),
        ).with_for_update()
        row = await db.scalar(stmt)
        values = obj.model_dump()
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            row = WorkerAuthorization(**values, approved_by=WorkforceService.operator_id())
            db.add(row)
        row.approved_by = WorkforceService.operator_id()
        await db.flush()
        return WorkerAuthorizationDetail.model_validate(row)

    @staticmethod
    async def list_rosters(db: AsyncSession, work_date=None) -> list[WorkerRosterDetail]:
        stmt = select(WorkerRoster).where(WorkerRoster.deleted == 0)
        if work_date:
            stmt = stmt.where(WorkerRoster.work_date == work_date)
        rows = (await db.scalars(stmt.order_by(WorkerRoster.work_date.desc(), WorkerRoster.shift_id))).all()
        return [WorkerRosterDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_roster(db: AsyncSession, obj: WorkerRosterInput) -> WorkerRosterDetail:
        await WorkforceService._user(db, obj.user_id)
        await WorkforceService._active_ref(db, Shift, obj.shift_id, 'SHIFT_NOT_ACTIVE')
        await WorkforceService._active_ref(db, WorkCenter, obj.work_center_id, 'WORK_CENTER_NOT_ACTIVE')
        await WorkforceService._active_ref(db, JobType, obj.job_type_id, 'JOB_TYPE_NOT_ACTIVE')
        row = await db.scalar(select(WorkerRoster).where(WorkerRoster.user_id == obj.user_id, WorkerRoster.work_date == obj.work_date, WorkerRoster.shift_id == obj.shift_id, WorkerRoster.deleted == 0).with_for_update())
        if row:
            for key, value in obj.model_dump().items():
                setattr(row, key, value)
        else:
            row = WorkerRoster(**obj.model_dump())
            db.add(row)
        await db.flush()
        return WorkerRosterDetail.model_validate(row)

    @staticmethod
    async def _has_active_roster(db: AsyncSession, user_id: int, job_type_id: int, work_center_id: int, now: datetime) -> bool:
        dates = [now.date(), now.date() - timedelta(days=1)]
        rows = (await db.execute(
            select(WorkerRoster, Shift).join(Shift, Shift.id == WorkerRoster.shift_id).where(
                WorkerRoster.user_id == user_id,
                WorkerRoster.job_type_id == job_type_id,
                WorkerRoster.work_center_id == work_center_id,
                WorkerRoster.work_date.in_(dates),
                WorkerRoster.status == RosterStatus.CONFIRMED,
                WorkerRoster.deleted == 0,
                Shift.status == ConfigStatus.ACTIVE,
                Shift.deleted == 0,
            )
        )).all()
        for roster, shift in rows:
            start_at = datetime.combine(roster.work_date, shift.start_time, tzinfo=timezone.tz_info)
            end_date = roster.work_date + timedelta(days=1) if shift.spans_next_day else roster.work_date
            end_at = datetime.combine(end_date, shift.end_time, tzinfo=timezone.tz_info)
            if start_at <= now <= end_at:
                return True
        return False

    @staticmethod
    async def check_access(db: AsyncSession, user_id: int | None, operation_id: int, work_center_id: int | None, *, now: datetime | None = None) -> AccessCheckResult:
        stmt = select(PositionQualificationRule).where(
            PositionQualificationRule.status == ConfigStatus.ACTIVE,
            PositionQualificationRule.deleted == 0,
            or_(PositionQualificationRule.operation_id == operation_id, PositionQualificationRule.operation_id.is_(None)),
        )
        if work_center_id is None:
            stmt = stmt.where(PositionQualificationRule.work_center_id.is_(None))
        else:
            stmt = stmt.where(or_(PositionQualificationRule.work_center_id == work_center_id, PositionQualificationRule.work_center_id.is_(None)))
        rules = list((await db.scalars(stmt.order_by(PositionQualificationRule.operation_id.desc(), PositionQualificationRule.id))).all())
        if not rules:
            return AccessCheckResult(allowed=True, enforcement_enabled=False)
        if not user_id:
            return AccessCheckResult(allowed=False, enforcement_enabled=True, reasons=['OPERATOR_ID_REQUIRED'])
        current = now or timezone.now()
        today = current.date()
        all_reasons: list[str] = []
        for rule in rules:
            reasons: list[str] = []
            level_rank = await db.scalar(
                select(SkillLevel.rank_order)
                .join(WorkerSkill, WorkerSkill.skill_level_id == SkillLevel.id)
                .where(
                    WorkerSkill.user_id == user_id,
                    WorkerSkill.job_type_id == rule.job_type_id,
                    WorkerSkill.status == QualificationStatus.ACTIVE,
                    WorkerSkill.deleted == 0,
                    SkillLevel.status == ConfigStatus.ACTIVE,
                    SkillLevel.deleted == 0,
                    or_(WorkerSkill.expires_on.is_(None), WorkerSkill.expires_on >= today),
                )
            )
            minimum_rank = await db.scalar(select(SkillLevel.rank_order).where(SkillLevel.id == rule.minimum_skill_level_id, SkillLevel.deleted == 0))
            if level_rank is None:
                reasons.append('SKILL_MISSING_OR_EXPIRED')
            elif minimum_rank is None or level_rank < minimum_rank:
                reasons.append('SKILL_LEVEL_INSUFFICIENT')
            if rule.required_certificate_type:
                certificate = await db.scalar(select(WorkerCertificate.id).where(
                    WorkerCertificate.user_id == user_id,
                    WorkerCertificate.certificate_type == rule.required_certificate_type,
                    WorkerCertificate.status == QualificationStatus.ACTIVE,
                    WorkerCertificate.valid_from <= today,
                    WorkerCertificate.expires_on >= today,
                    WorkerCertificate.deleted == 0,
                ))
                if not certificate:
                    reasons.append('CERTIFICATE_MISSING_OR_EXPIRED')
            if rule.require_authorization:
                auth = await db.scalar(select(WorkerAuthorization.id).where(
                    WorkerAuthorization.user_id == user_id,
                    WorkerAuthorization.job_type_id == rule.job_type_id,
                    WorkerAuthorization.work_center_id == work_center_id,
                    WorkerAuthorization.status == QualificationStatus.ACTIVE,
                    WorkerAuthorization.effective_from <= today,
                    or_(WorkerAuthorization.effective_to.is_(None), WorkerAuthorization.effective_to >= today),
                    or_(WorkerAuthorization.operation_id.is_(None), WorkerAuthorization.operation_id == operation_id),
                    WorkerAuthorization.deleted == 0,
                ))
                if not auth:
                    reasons.append('POSITION_AUTHORIZATION_MISSING_OR_EXPIRED')
            if rule.require_roster and (work_center_id is None or not await WorkforceService._has_active_roster(db, user_id, rule.job_type_id, work_center_id, current)):
                reasons.append('ACTIVE_SHIFT_ROSTER_MISSING')
            if not reasons:
                return AccessCheckResult(allowed=True, enforcement_enabled=True, matched_rule_id=rule.id)
            all_reasons.extend(f'{rule.rule_code}:{reason}' for reason in reasons)
        return AccessCheckResult(allowed=False, enforcement_enabled=True, reasons=all_reasons)

    @staticmethod
    async def enforce_access(db: AsyncSession, user_id: int | None, operation_id: int, work_center_id: int | None) -> None:
        result = await WorkforceService.check_access(db, user_id, operation_id, work_center_id)
        if not result.allowed:
            raise errors.ConflictError(msg=f'OPERATOR_QUALIFICATION_DENIED:{";".join(result.reasons)}')

    @staticmethod
    async def dashboard(db: AsyncSession) -> WorkforceDashboard:
        today = timezone.now().date()
        in_30_days = today + timedelta(days=30)
        async def count(stmt):
            return int(await db.scalar(stmt) or 0)
        return WorkforceDashboard(
            active_job_types=await count(select(func.count(JobType.id)).where(JobType.status == ConfigStatus.ACTIVE, JobType.deleted == 0)),
            active_skill_levels=await count(select(func.count(SkillLevel.id)).where(SkillLevel.status == ConfigStatus.ACTIVE, SkillLevel.deleted == 0)),
            qualified_workers=await count(select(func.count(func.distinct(WorkerSkill.user_id))).where(WorkerSkill.status == QualificationStatus.ACTIVE, or_(WorkerSkill.expires_on.is_(None), WorkerSkill.expires_on >= today), WorkerSkill.deleted == 0)),
            certificates_expiring_30_days=await count(select(func.count(WorkerCertificate.id)).where(WorkerCertificate.status == QualificationStatus.ACTIVE, WorkerCertificate.expires_on.between(today, in_30_days), WorkerCertificate.deleted == 0)),
            expired_certificates=await count(select(func.count(WorkerCertificate.id)).where(WorkerCertificate.expires_on < today, WorkerCertificate.deleted == 0)),
            active_authorizations=await count(select(func.count(WorkerAuthorization.id)).where(WorkerAuthorization.status == QualificationStatus.ACTIVE, WorkerAuthorization.effective_from <= today, or_(WorkerAuthorization.effective_to.is_(None), WorkerAuthorization.effective_to >= today), WorkerAuthorization.deleted == 0)),
            confirmed_today_rosters=await count(select(func.count(WorkerRoster.id)).where(WorkerRoster.work_date == today, WorkerRoster.status == RosterStatus.CONFIRMED, WorkerRoster.deleted == 0)),
            active_rules=await count(select(func.count(PositionQualificationRule.id)).where(PositionQualificationRule.status == ConfigStatus.ACTIVE, PositionQualificationRule.deleted == 0)),
        )


workforce_service = WorkforceService()
