from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.production.enums import AndonEventType, AndonPriority, AndonStatus


class ProductionAndonEvent(Base):
    """现场异常事件 covering stoppage, material shortage and quality blockers."""

    __tablename__ = 'mes_production_andon_event'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_andon_work_order'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_andon_operation'),
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_andon_equipment'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_andon_material'),
        sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_andon_ncr'),
        sa.UniqueConstraint('event_no', 'deleted', name='uk_andon_event_no'),
        sa.Index('idx_andon_status_priority', 'status', 'priority'),
        sa.Index('idx_andon_sla_due', 'status', 'sla_due_at'),
        sa.Index('idx_andon_work_order', 'work_order_id', 'created_time'),
        {'comment': 'MES production Andon abnormal events'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    event_no: Mapped[str] = mapped_column(sa.String(100))
    event_type: Mapped[AndonEventType] = mapped_column(sa.String(30))
    title: Mapped[str] = mapped_column(sa.String(200))
    description: Mapped[str] = mapped_column(UniversalText)
    occurred_at: Mapped[datetime] = mapped_column(TimeZone)
    sla_due_at: Mapped[datetime] = mapped_column(TimeZone)
    priority: Mapped[AndonPriority] = mapped_column(sa.String(20), default=AndonPriority.MEDIUM, server_default=AndonPriority.MEDIUM.value)
    status: Mapped[AndonStatus] = mapped_column(sa.String(30), default=AndonStatus.OPEN, server_default=AndonStatus.OPEN.value)
    work_order_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    work_order_operation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    equipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    material_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    ncr_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reporter_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    assignee_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    escalation_level: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    root_cause: Mapped[str | None] = mapped_column(UniversalText, default=None)
    resolution_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ProductionAndonAssignment(Base):
    """Dispatch record for assigning an Andon event to a responder/team."""

    __tablename__ = 'mes_production_andon_assignment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['event_id'], ['mes_production_andon_event.id'], name='fk_andon_assignment_event'),
        sa.Index('idx_andon_assignment_event_time', 'event_id', 'assigned_at'),
        {'comment': 'MES Andon dispatch assignments'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    event_id: Mapped[int] = mapped_column(sa.BigInteger)
    assignee_id: Mapped[int] = mapped_column(sa.BigInteger)
    assigned_at: Mapped[datetime] = mapped_column(TimeZone)
    assigned_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ProductionAndonAction(Base):
    """Append-only Andon state transition and escalation audit."""

    __tablename__ = 'mes_production_andon_action'
    __table_args__ = (
        sa.ForeignKeyConstraint(['event_id'], ['mes_production_andon_event.id'], name='fk_andon_action_event'),
        sa.Index('idx_andon_action_event_time', 'event_id', 'acted_at'),
        {'comment': 'MES Andon action history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    event_id: Mapped[int] = mapped_column(sa.BigInteger)
    action: Mapped[str] = mapped_column(sa.String(30))
    acted_at: Mapped[datetime] = mapped_column(TimeZone)
    from_status: Mapped[AndonStatus | None] = mapped_column(sa.String(30), default=None)
    to_status: Mapped[AndonStatus | None] = mapped_column(sa.String(30), default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    acted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
