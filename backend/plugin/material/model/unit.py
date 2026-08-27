import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.material.enums import UnitStatus


class UnitOfMeasure(Base):
    """Base unit of measure used by material master data."""

    __tablename__ = 'mes_unit'
    __table_args__ = (
        sa.UniqueConstraint('unit_code', 'deleted', name='uk_mes_unit_code_deleted'),
        sa.Index('idx_mes_unit_status', 'status'),
        {'comment': 'MES unit of measure'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    unit_code: Mapped[str] = mapped_column(sa.String(20), comment='Unit code')
    unit_name: Mapped[str] = mapped_column(sa.String(50), comment='Unit name')
    symbol: Mapped[str | None] = mapped_column(sa.String(20), default=None)
    status: Mapped[UnitStatus] = mapped_column(
        sa.String(20), default=UnitStatus.ACTIVE, server_default=UnitStatus.ACTIVE.value
    )
    decimal_places: Mapped[int] = mapped_column(default=0, server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
