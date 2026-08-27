from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.routing.enums import RunTimeUnit


class RoutingOperation(Base):
    """A product-specific operation configuration in a linear routing."""

    __tablename__ = 'mes_routing_operation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['routing_id'], ['mes_routing.id'], name='fk_mes_routing_operation_routing'),
        sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_mes_routing_operation_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_mes_routing_operation_work_center'),
        sa.UniqueConstraint('routing_id', 'sequence_no', 'deleted', name='uk_mes_routing_operation_sequence_deleted'),
        sa.Index('idx_mes_routing_operation_routing', 'routing_id'),
        sa.Index('idx_mes_routing_operation_operation', 'operation_id'),
        sa.Index('idx_mes_routing_operation_work_center', 'work_center_id'),
        {'comment': 'MES configured operations in a routing version'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    routing_id: Mapped[int] = mapped_column(sa.BigInteger, comment='工艺路线 ID')
    sequence_no: Mapped[int] = mapped_column(sa.Integer, comment='工序顺序号')
    operation_id: Mapped[int] = mapped_column(sa.BigInteger, comment='标准工序 ID')
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    operation_name_override: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    operation_name_snapshot: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    setup_time_min: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    run_time_value: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    run_time_unit: Mapped[RunTimeUnit] = mapped_column(
        sa.String(30), default=RunTimeUnit.MIN_PER_BASE_QTY, server_default=RunTimeUnit.MIN_PER_BASE_QTY.value
    )
    queue_time_min: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    move_time_min: Mapped[Decimal] = mapped_column(sa.Numeric(18, 4), default=Decimal('0'), server_default='0')
    standard_yield_rate: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), default=Decimal('100'), server_default='100')
    reporting_required: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    quality_required: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    trace_required: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
