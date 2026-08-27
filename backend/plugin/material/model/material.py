import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.material.enums import MaterialStatus, MaterialType


class Material(Base):
    """Enterprise material master data, without inventory quantities."""

    __tablename__ = 'mes_material'
    __table_args__ = (
        sa.ForeignKeyConstraint(['category_id'], ['mes_material_category.id'], name='fk_mes_material_category'),
        sa.ForeignKeyConstraint(['base_unit_id'], ['mes_unit.id'], name='fk_mes_material_unit'),
        sa.ForeignKeyConstraint(['default_warehouse_id'], ['mes_warehouse.id'], name='fk_mes_material_warehouse'),
        sa.UniqueConstraint('material_code', 'deleted', name='uk_mes_material_code_deleted'),
        sa.Index('idx_mes_material_category', 'category_id'),
        sa.Index('idx_mes_material_type', 'material_type'),
        sa.Index('idx_mes_material_status', 'status'),
        sa.Index('idx_mes_material_name', 'material_name'),
        sa.Index('idx_mes_material_warehouse', 'default_warehouse_id'),
        {'comment': 'MES material master data'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    material_code: Mapped[str] = mapped_column(sa.String(80), comment='Material code')
    material_name: Mapped[str] = mapped_column(sa.String(200), comment='Material name')
    material_type: Mapped[MaterialType] = mapped_column(sa.String(30), comment='Material type')
    category_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Material category ID')
    base_unit_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Base unit ID')
    material_short_name: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    specification: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    model: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    status: Mapped[MaterialStatus] = mapped_column(
        sa.String(20), default=MaterialStatus.ACTIVE, server_default=MaterialStatus.ACTIVE.value
    )
    batch_control: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    serial_control: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    purchasable: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    producible: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    sellable: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    quality_inspection_required: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    default_warehouse_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    shelf_life_days: Mapped[int | None] = mapped_column(sa.Integer, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
