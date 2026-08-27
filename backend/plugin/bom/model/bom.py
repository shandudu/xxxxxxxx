from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.bom.enums import BomStatus


class Bom(Base):
    """Versioned bill of materials header."""

    __tablename__ = 'mes_bom'
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['product_material_id'], ['mes_material.id'], name='fk_mes_bom_product_material'
        ),
        sa.UniqueConstraint('bom_code', 'deleted', name='uk_mes_bom_code_deleted'),
        sa.UniqueConstraint(
            'product_material_id', 'bom_version', 'deleted', name='uk_mes_bom_product_version_deleted'
        ),
        sa.Index('idx_mes_bom_product_material', 'product_material_id'),
        sa.Index('idx_mes_bom_status', 'status'),
        sa.Index('idx_mes_bom_default', 'product_material_id', 'is_default'),
        sa.Index('idx_mes_bom_effective_from', 'effective_from'),
        sa.Index('idx_mes_bom_effective_to', 'effective_to'),
        {'comment': 'MES versioned bill of materials'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    bom_code: Mapped[str] = mapped_column(sa.String(80), comment='Business BOM code')
    product_material_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Product material ID')
    bom_version: Mapped[str] = mapped_column(sa.String(30), comment='BOM version')
    base_quantity: Mapped[Decimal] = mapped_column(
        sa.Numeric(18, 6), default=1, server_default='1', comment='BOM base quantity'
    )
    status: Mapped[BomStatus] = mapped_column(
        sa.String(20), default=BomStatus.DRAFT, server_default=BomStatus.DRAFT.value, comment='BOM status'
    )
    effective_from: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    effective_to: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    is_default: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
