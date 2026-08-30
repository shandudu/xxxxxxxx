from collections import Counter
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.production.enums import AndonEventType, AndonStatus
from backend.plugin.production.model import ProductionAndonAction, ProductionAndonAssignment, ProductionAndonEvent
from backend.plugin.production.schema.production import AndonDashboard, AndonEventDetail, AssignAndonEvent, CreateAndonEvent, ResolveAndonEvent
from backend.utils.timezone import timezone


class AndonService:
    SLA_HOURS = {
        AndonEventType.STOPPAGE: 2,
        AndonEventType.MATERIAL_SHORTAGE: 4,
        AndonEventType.QUALITY: 8,
    }

    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _event(db: AsyncSession, event_id: int, lock: bool = False) -> ProductionAndonEvent:
        statement = select(ProductionAndonEvent).where(ProductionAndonEvent.id == event_id, ProductionAndonEvent.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        event = await db.scalar(statement)
        if not event:
            raise errors.NotFoundError(msg='ANDON_EVENT_NOT_FOUND')
        return event

    @staticmethod
    async def _action(db: AsyncSession, event: ProductionAndonEvent, action: str, previous: AndonStatus | None, notes: str | None = None) -> None:
        db.add(ProductionAndonAction(event_id=event.id, action=action, from_status=previous, to_status=event.status, notes=notes, acted_by=AndonService._operator_id(), acted_at=timezone.now()))

    @staticmethod
    async def create(db: AsyncSession, obj: CreateAndonEvent) -> AndonEventDetail:
        occurred_at = obj.occurred_at or timezone.now()
        event = ProductionAndonEvent(
            event_no=f'ANDON-{occurred_at:%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            event_type=obj.event_type, title=obj.title, description=obj.description,
            occurred_at=occurred_at, sla_due_at=occurred_at + timedelta(hours=AndonService.SLA_HOURS[obj.event_type]),
            priority=obj.priority, work_order_id=obj.work_order_id, work_order_operation_id=obj.work_order_operation_id,
            equipment_id=obj.equipment_id, material_id=obj.material_id, ncr_id=obj.ncr_id,
            reporter_id=AndonService._operator_id(),
        )
        db.add(event)
        await db.flush()
        await AndonService._action(db, event, 'CREATED', None, obj.description)
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def list_events(db: AsyncSession, status: str | None = None, event_type: str | None = None) -> list[AndonEventDetail]:
        statement = select(ProductionAndonEvent).where(ProductionAndonEvent.deleted == 0)
        if status:
            statement = statement.where(ProductionAndonEvent.status == status)
        if event_type:
            statement = statement.where(ProductionAndonEvent.event_type == event_type)
        rows = (await db.scalars(statement.order_by(ProductionAndonEvent.priority.desc(), ProductionAndonEvent.occurred_at.desc()))).all()
        return [AndonEventDetail.model_validate(row) for row in rows]

    @staticmethod
    async def get(db: AsyncSession, event_id: int) -> AndonEventDetail:
        return AndonEventDetail.model_validate(await AndonService._event(db, event_id))

    @staticmethod
    async def assign(db: AsyncSession, event_id: int, obj: AssignAndonEvent) -> AndonEventDetail:
        event = await AndonService._event(db, event_id, lock=True)
        if event.status in (AndonStatus.RESOLVED, AndonStatus.CANCELLED):
            raise errors.ConflictError(msg='ANDON_EVENT_NOT_ASSIGNABLE')
        previous = event.status
        event.assignee_id = obj.assignee_id
        event.status = AndonStatus.ACKNOWLEDGED if event.status == AndonStatus.OPEN else event.status
        event.acknowledged_at = event.acknowledged_at or timezone.now()
        db.add(ProductionAndonAssignment(event_id=event.id, assignee_id=obj.assignee_id, assigned_by=AndonService._operator_id(), assigned_at=timezone.now(), notes=obj.notes))
        await AndonService._action(db, event, 'ASSIGNED', previous, obj.notes)
        await db.flush()
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def start(db: AsyncSession, event_id: int) -> AndonEventDetail:
        event = await AndonService._event(db, event_id, lock=True)
        if event.status in (AndonStatus.RESOLVED, AndonStatus.CANCELLED):
            raise errors.ConflictError(msg='ANDON_EVENT_NOT_STARTABLE')
        previous = event.status
        event.status = AndonStatus.IN_PROGRESS
        event.started_at = event.started_at or timezone.now()
        assignment = await db.scalar(select(ProductionAndonAssignment).where(ProductionAndonAssignment.event_id == event.id, ProductionAndonAssignment.deleted == 0).order_by(ProductionAndonAssignment.assigned_at.desc()))
        if assignment and assignment.accepted_at is None:
            assignment.accepted_at = timezone.now()
        await AndonService._action(db, event, 'STARTED', previous)
        await db.flush()
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def resolve(db: AsyncSession, event_id: int, obj: ResolveAndonEvent) -> AndonEventDetail:
        event = await AndonService._event(db, event_id, lock=True)
        if event.status == AndonStatus.RESOLVED:
            return AndonEventDetail.model_validate(event)
        if event.status == AndonStatus.CANCELLED:
            raise errors.ConflictError(msg='ANDON_EVENT_NOT_RESOLVABLE')
        previous = event.status
        event.status = AndonStatus.RESOLVED
        event.resolved_at = timezone.now()
        event.root_cause = obj.root_cause
        event.resolution_notes = obj.resolution_notes
        assignment = await db.scalar(select(ProductionAndonAssignment).where(ProductionAndonAssignment.event_id == event.id, ProductionAndonAssignment.deleted == 0).order_by(ProductionAndonAssignment.assigned_at.desc()))
        if assignment:
            assignment.completed_at = timezone.now()
        await AndonService._action(db, event, 'RESOLVED', previous, obj.resolution_notes)
        await db.flush()
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def escalate(db: AsyncSession, event_id: int, notes: str | None = None) -> AndonEventDetail:
        event = await AndonService._event(db, event_id, lock=True)
        if event.status in (AndonStatus.RESOLVED, AndonStatus.CANCELLED):
            raise errors.ConflictError(msg='ANDON_EVENT_NOT_ESCALATABLE')
        previous = event.status
        event.escalation_level += 1
        event.status = AndonStatus.BLOCKED
        await AndonService._action(db, event, 'ESCALATED', previous, notes or f'升级到第 {event.escalation_level} 级')
        await db.flush()
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def cancel(db: AsyncSession, event_id: int) -> AndonEventDetail:
        event = await AndonService._event(db, event_id, lock=True)
        if event.status == AndonStatus.RESOLVED:
            raise errors.ConflictError(msg='ANDON_EVENT_NOT_CANCELLABLE')
        previous = event.status
        event.status = AndonStatus.CANCELLED
        await AndonService._action(db, event, 'CANCELLED', previous)
        await db.flush()
        return AndonEventDetail.model_validate(event)

    @staticmethod
    async def list_assignments(db: AsyncSession, event_id: int) -> list[ProductionAndonAssignment]:
        await AndonService._event(db, event_id)
        return list((await db.scalars(select(ProductionAndonAssignment).where(ProductionAndonAssignment.event_id == event_id, ProductionAndonAssignment.deleted == 0).order_by(ProductionAndonAssignment.assigned_at.desc()))).all())

    @staticmethod
    async def list_actions(db: AsyncSession, event_id: int) -> list[ProductionAndonAction]:
        await AndonService._event(db, event_id)
        return list((await db.scalars(select(ProductionAndonAction).where(ProductionAndonAction.event_id == event_id, ProductionAndonAction.deleted == 0).order_by(ProductionAndonAction.acted_at))).all())

    @staticmethod
    async def dashboard(db: AsyncSession) -> AndonDashboard:
        events = list((await db.scalars(select(ProductionAndonEvent).where(ProductionAndonEvent.deleted == 0))).all())
        now = timezone.now()
        active = [event for event in events if event.status not in (AndonStatus.RESOLVED, AndonStatus.CANCELLED)]
        resolved_durations = [(event.resolved_at - event.occurred_at).total_seconds() / 3600 for event in events if event.resolved_at]
        return AndonDashboard(
            status_counts=dict(Counter(str(event.status) for event in events)),
            type_counts=dict(Counter(str(event.event_type) for event in events)),
            priority_counts=dict(Counter(str(event.priority) for event in events)),
            active_count=len(active),
            overdue_count=sum(1 for event in active if event.sla_due_at <= now),
            average_resolve_hours=Decimal(str(round(sum(resolved_durations) / len(resolved_durations), 2) if resolved_durations else 0)),
        )


andon_service = AndonService()
