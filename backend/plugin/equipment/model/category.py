import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.equipment.enums import EquipmentCategoryStatus


class EquipmentCategory(Base):
    """Hierarchical MES equipment category."""

    __tablename__ = 'mes_equipment_category'
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['parent_id'], ['mes_equipment_category.id'], name='fk_mes_equipment_category_parent'
        ),
        sa.UniqueConstraint('category_code', 'deleted', name='uk_mes_equipment_category_code_deleted'),
        sa.Index('idx_mes_equipment_category_parent', 'parent_id'),
        sa.Index('idx_mes_equipment_category_status', 'status'),
        sa.Index('idx_mes_equipment_category_sort', 'sort_no'),
        {'comment': 'MES equipment category tree'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    category_code: Mapped[str] = mapped_column(sa.String(50), comment='Equipment category code')
    category_name: Mapped[str] = mapped_column(sa.String(100), comment='Equipment category name')
    parent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Parent category ID')
    status: Mapped[EquipmentCategoryStatus] = mapped_column(
        sa.String(20),
        default=EquipmentCategoryStatus.ACTIVE,
        server_default=EquipmentCategoryStatus.ACTIVE.value,
    )
    sort_no: Mapped[int] = mapped_column(default=0, server_default='0')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
