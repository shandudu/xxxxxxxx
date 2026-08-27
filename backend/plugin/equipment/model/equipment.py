from datetime import date
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.equipment.enums import EquipmentStatus, EquipmentType


class Equipment(Base):
    """MES equipment master record; it does not contain live machine telemetry."""

    __tablename__ = 'mes_equipment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['category_id'], ['mes_equipment_category.id'], name='fk_mes_equipment_category'),
        sa.UniqueConstraint('equipment_code', 'deleted', name='uk_mes_equipment_code_deleted'),
        sa.Index('idx_mes_equipment_category', 'category_id'),
        sa.Index('idx_mes_equipment_status', 'status'),
        sa.Index('idx_mes_equipment_enabled', 'enabled'),
        sa.Index('idx_mes_equipment_type', 'equipment_type'),
        sa.Index('idx_mes_equipment_factory', 'factory_code'),
        sa.Index('idx_mes_equipment_name', 'equipment_name'),
        {'comment': 'MES equipment master data'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    equipment_code: Mapped[str] = mapped_column(sa.String(80), comment='Equipment code')
    equipment_name: Mapped[str] = mapped_column(sa.String(150), comment='Equipment name')
    category_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Equipment category ID')
    equipment_type: Mapped[EquipmentType] = mapped_column(sa.String(30), comment='Equipment type')
    model: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    manufacturer: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    serial_number: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    factory_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    area_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    installation_location: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    status: Mapped[EquipmentStatus] = mapped_column(
        sa.String(30), default=EquipmentStatus.IDLE, server_default=EquipmentStatus.IDLE.value
    )
    enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    production_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    data_collection_enabled: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    maintenance_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    commission_date: Mapped[date | None] = mapped_column(sa.Date, default=None)
    service_date: Mapped[date | None] = mapped_column(sa.Date, default=None)
    rated_capacity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    capacity_unit: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
