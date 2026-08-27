import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.warehouse.enums import LocationStatus, LocationType


class Location(Base):
    """MES physical storage location."""

    __tablename__ = 'mes_location'
    __table_args__ = (
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_mes_location_warehouse'),
        sa.ForeignKeyConstraint(['area_id'], ['mes_area.id'], name='fk_mes_location_area'),
        sa.ForeignKeyConstraint(['parent_id'], ['mes_location.id'], name='fk_mes_location_parent'),
        sa.UniqueConstraint('location_code', 'deleted', name='uk_mes_location_code_deleted'),
        sa.Index('idx_mes_location_warehouse', 'warehouse_id'),
        sa.Index('idx_mes_location_area', 'area_id'),
        sa.Index('idx_mes_location_parent', 'parent_id'),
        sa.Index('idx_mes_location_status', 'status'),
        sa.Index('idx_mes_location_type', 'location_type'),
        {'comment': 'MES physical storage location'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    location_code: Mapped[str] = mapped_column(sa.String(80), comment='Location code')
    location_name: Mapped[str] = mapped_column(sa.String(100), comment='Location name')
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Warehouse ID')
    area_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Area ID')
    location_type: Mapped[LocationType] = mapped_column(sa.String(30), comment='Location type')
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Parent location ID')
    location_level: Mapped[int] = mapped_column(default=1, server_default='1')
    status: Mapped[LocationStatus] = mapped_column(
        sa.String(20), default=LocationStatus.AVAILABLE, server_default=LocationStatus.AVAILABLE.value
    )
    storage_enabled: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    capacity_value: Mapped[float | None] = mapped_column(sa.Numeric(18, 4), default=None)
    capacity_unit: Mapped[str | None] = mapped_column(sa.String(20), default=None)
    mixed_material_allowed: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    mixed_lot_allowed: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')
