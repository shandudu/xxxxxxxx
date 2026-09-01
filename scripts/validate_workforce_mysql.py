"""Run a rollback-only MySQL qualification access-control business check."""
from __future__ import annotations

import asyncio
from datetime import time, timedelta
from uuid import uuid4

from sqlalchemy import select

from backend.app.admin.model import User
from backend.database.db import async_db_session, async_engine
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
from backend.plugin.scheduling.service.workforce_service import workforce_service
from backend.utils.timezone import timezone


async def main() -> None:
    async with async_db_session() as db:
        transaction = await db.begin()
        try:
            user_id = await db.scalar(select(User.id).where(User.status == 1, User.deleted == 0).limit(1))
            operation_id = await db.scalar(select(Operation.id).where(Operation.deleted == 0).limit(1))
            work_center_id = await db.scalar(select(WorkCenter.id).where(WorkCenter.deleted == 0).limit(1))
            if not all((user_id, operation_id, work_center_id)):
                raise RuntimeError('Validation requires one active user, operation, and work center')
            token = uuid4().hex[:8].upper()
            now = timezone.now()
            today = now.date()
            job = JobType(job_code=f'VALJOB{token}', job_name='Validation operator', status=ConfigStatus.ACTIVE)
            junior = SkillLevel(level_code=f'VALJ{token}', level_name='Validation junior', rank_order=800000 + int(token[:4], 16), status=ConfigStatus.ACTIVE)
            senior = SkillLevel(level_code=f'VALS{token}', level_name='Validation senior', rank_order=900000 + int(token[:4], 16), status=ConfigStatus.ACTIVE)
            shift = Shift(shift_code=f'VAL{token}', shift_name='Validation all-day shift', start_time=time(0), end_time=time(23, 59), spans_next_day=False, break_minutes=0, status=ConfigStatus.ACTIVE)
            db.add_all([job, junior, senior, shift])
            await db.flush()
            rule = PositionQualificationRule(
                rule_code=f'VALRULE{token}', rule_name='Validation guarded operation', job_type_id=job.id,
                minimum_skill_level_id=senior.id, operation_id=operation_id, work_center_id=work_center_id,
                required_certificate_type=f'VALCERT{token}', require_authorization=True, require_roster=True,
                status=ConfigStatus.ACTIVE,
            )
            db.add(rule)
            await db.flush()
            denied = await workforce_service.check_access(db, user_id, operation_id, work_center_id, now=now)
            assert denied.enforcement_enabled and not denied.allowed
            assert any('SKILL_MISSING_OR_EXPIRED' in reason for reason in denied.reasons)
            db.add_all([
                WorkerSkill(user_id=user_id, job_type_id=job.id, skill_level_id=senior.id, assessed_on=today, expires_on=today + timedelta(days=365), status=QualificationStatus.ACTIVE),
                WorkerCertificate(user_id=user_id, certificate_type=f'VALCERT{token}', certificate_name='Validation certificate', certificate_no=f'VALNO{token}', issued_on=today, valid_from=today, expires_on=today + timedelta(days=365), status=QualificationStatus.ACTIVE),
                WorkerAuthorization(user_id=user_id, job_type_id=job.id, work_center_id=work_center_id, effective_from=today, operation_id=operation_id, effective_to=today + timedelta(days=365), status=QualificationStatus.ACTIVE),
                WorkerRoster(user_id=user_id, work_date=today, shift_id=shift.id, work_center_id=work_center_id, job_type_id=job.id, status=RosterStatus.CONFIRMED),
            ])
            await db.flush()
            allowed = await workforce_service.check_access(db, user_id, operation_id, work_center_id, now=now)
            assert allowed.allowed and allowed.matched_rule_id == rule.id
            no_rule = await workforce_service.check_access(db, user_id, operation_id + 10**9, work_center_id + 10**9, now=now)
            assert no_rule.allowed and not no_rule.enforcement_enabled
            print('OK: qualification denial, full qualification pass, and unconfigured-scope compatibility pass')
        finally:
            await transaction.rollback()
    await async_engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
