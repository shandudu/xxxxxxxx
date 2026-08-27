import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.routing.enums import OperationStatus, OperationType


class Operation(Base):
    """Reusable MES standard operation."""

    __tablename__ = 'mes_operation'
    __table_args__ = (
        sa.UniqueConstraint('operation_code', 'deleted', name='uk_mes_operation_code_deleted'),
        sa.Index('idx_mes_operation_status', 'status'),
        sa.Index('idx_mes_operation_type', 'operation_type'),
        {'comment': 'MES reusable standard operations'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    operation_code: Mapped[str] = mapped_column(sa.String(80), comment='工序编码')
    operation_name: Mapped[str] = mapped_column(sa.String(150), comment='工序名称')
    operation_short_name: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    operation_type: Mapped[OperationType] = mapped_column(
        sa.String(30), default=OperationType.PROCESS, server_default=OperationType.PROCESS.value
    )
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    status: Mapped[OperationStatus] = mapped_column(
        sa.String(20), default=OperationStatus.ACTIVE, server_default=OperationStatus.ACTIVE.value
    )
    production_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    quality_enabled: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    trace_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
