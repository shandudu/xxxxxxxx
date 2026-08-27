from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key


class BomItem(Base):
    """Component line in a BOM version."""

    __tablename__ = 'mes_bom_item'
    __table_args__ = (
        sa.ForeignKeyConstraint(['bom_id'], ['mes_bom.id'], name='fk_mes_bom_item_bom'),
        sa.ForeignKeyConstraint(
            ['component_material_id'], ['mes_material.id'], name='fk_mes_bom_item_component_material'
        ),
        sa.ForeignKeyConstraint(['unit_id'], ['mes_unit.id'], name='fk_mes_bom_item_unit'),
        sa.UniqueConstraint('bom_id', 'line_no', 'deleted', name='uk_mes_bom_item_line_deleted'),
        sa.Index('idx_mes_bom_item_bom', 'bom_id'),
        sa.Index('idx_mes_bom_item_component_material', 'component_material_id'),
        {'comment': 'MES BOM component lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    bom_id: Mapped[int] = mapped_column(sa.BigInteger, comment='BOM ID')
    line_no: Mapped[int] = mapped_column(sa.Integer, comment='BOM line number')
    component_material_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Component material ID')
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), comment='Standard component quantity')
    unit_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Component base unit ID')
    loss_rate: Mapped[Decimal] = mapped_column(
        sa.Numeric(8, 4), default=0, server_default='0', comment='Percentage loss rate'
    )
    fixed_loss_qty: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 6), default=0, server_default='0', comment='Fixed loss quantity'
    )
    is_optional: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
