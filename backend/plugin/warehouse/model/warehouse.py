import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.warehouse.enums import WarehouseStatus, WarehouseType


class Warehouse(Base):
    """MES warehouse master data."""

    __tablename__ = 'mes_warehouse'
    __table_args__ = (
        sa.UniqueConstraint('warehouse_code', 'deleted', name='uk_mes_warehouse_code_deleted'),
        sa.Index('idx_mes_warehouse_status', 'status'),
        sa.Index('idx_mes_warehouse_type', 'warehouse_type'),
        {'comment': 'MES warehouse configuration'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    warehouse_code: Mapped[str] = mapped_column(sa.String(50), comment='Warehouse code')
    warehouse_name: Mapped[str] = mapped_column(sa.String(100), comment='Warehouse name')
    warehouse_type: Mapped[WarehouseType] = mapped_column(sa.String(30), comment='Warehouse type')
    factory_code: Mapped[str | None] = mapped_column(sa.String(50), default=None, comment='Factory code')
    status: Mapped[WarehouseStatus] = mapped_column(
        sa.String(20), default=WarehouseStatus.ACTIVE, server_default=WarehouseStatus.ACTIVE.value
    )
    allow_inbound: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    allow_outbound: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)

