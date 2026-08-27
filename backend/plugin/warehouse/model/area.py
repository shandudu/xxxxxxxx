import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.warehouse.enums import AreaStatus, AreaType


class Area(Base):
    """MES warehouse area."""

    __tablename__ = 'mes_area'
    __table_args__ = (
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_mes_area_warehouse'),
        sa.UniqueConstraint('warehouse_id', 'area_code', 'deleted', name='uk_mes_area_warehouse_code_deleted'),
        sa.Index('idx_mes_area_warehouse', 'warehouse_id'),
        sa.Index('idx_mes_area_status', 'status'),
        {'comment': 'MES warehouse area'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    area_code: Mapped[str] = mapped_column(sa.String(50), comment='Area code')
    area_name: Mapped[str] = mapped_column(sa.String(100), comment='Area name')
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Warehouse ID')
    area_type: Mapped[AreaType | None] = mapped_column(sa.String(30), default=None)
    status: Mapped[AreaStatus] = mapped_column(
        sa.String(20), default=AreaStatus.ACTIVE, server_default=AreaStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')

