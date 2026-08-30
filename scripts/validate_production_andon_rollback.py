"""Validate production Andon creation, dispatch, escalation and recovery closure."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.production.enums import AndonEventType, AndonStatus
from backend.plugin.production.model import ProductionAndonAction, ProductionAndonAssignment
from backend.plugin.production.schema.production import AssignAndonEvent, CreateAndonEvent, ResolveAndonEvent
from backend.plugin.production.service import andon_service


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                event = await andon_service.create(db, CreateAndonEvent(event_type=AndonEventType.STOPPAGE, title='Andon rollback validation', description='验证现场停机闭环'))
                await andon_service.assign(db, event.id, AssignAndonEvent(assignee_id=1, notes='派工验证'))
                await andon_service.start(db, event.id)
                await andon_service.escalate(db, event.id, '升级验证')
                event = await andon_service.resolve(db, event.id, ResolveAndonEvent(root_cause='验证根因', resolution_notes='恢复并确认'))
                if event.status != AndonStatus.RESOLVED:
                    raise RuntimeError('Andon did not resolve')
                for action, expected in (
                    (
                        lambda: andon_service.assign(
                            db, event.id, AssignAndonEvent(assignee_id=2, notes='终态禁止派工')
                        ),
                        'ANDON_EVENT_NOT_ASSIGNABLE',
                    ),
                    (
                        lambda: andon_service.escalate(db, event.id, '终态禁止升级'),
                        'ANDON_EVENT_NOT_ESCALATABLE',
                    ),
                ):
                    try:
                        await action()
                    except errors.ConflictError as exc:
                        if exc.msg != expected:
                            raise
                    else:
                        raise RuntimeError(f'Andon terminal action was accepted: {expected}')
                assignments = list((await db.scalars(select(ProductionAndonAssignment).where(ProductionAndonAssignment.event_id == event.id))).all())
                actions = list((await db.scalars(select(ProductionAndonAction).where(ProductionAndonAction.event_id == event.id))).all())
                if len(assignments) != 1 or len(actions) < 4:
                    raise RuntimeError('Andon audit trail incomplete')
                dashboard = await andon_service.dashboard(db)
                print(f'PRODUCTION_ANDON_RUN_OK status={event.status} actions={len(actions)} active={dashboard.active_count}')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('PRODUCTION_ANDON_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
