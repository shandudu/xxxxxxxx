from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.routing.enums import RoutingStatus, RoutingType


class Routing(Base):
    """Versioned, linear manufacturing routing for one producible material."""

    __tablename__ = 'mes_routing'
    __table_args__ = (
        sa.ForeignKeyConstraint(['product_material_id'], ['mes_material.id'], name='fk_mes_routing_product_material'),
        sa.UniqueConstraint('routing_code', 'deleted', name='uk_mes_routing_code_deleted'),
        sa.UniqueConstraint(
            'product_material_id', 'routing_version', 'routing_type', 'deleted', name='uk_mes_routing_product_version_type_deleted'
        ),
        sa.Index('idx_mes_routing_product', 'product_material_id'),
        sa.Index('idx_mes_routing_status', 'status'),
        sa.Index('idx_mes_routing_type', 'routing_type'),
        sa.Index('idx_mes_routing_default', 'product_material_id', 'routing_type', 'is_default'),
        sa.Index('idx_mes_routing_effective_from', 'effective_from'),
        sa.Index('idx_mes_routing_effective_to', 'effective_to'),
        {'comment': 'MES versioned linear process routings'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    routing_code: Mapped[str] = mapped_column(sa.String(80), comment='工艺路线编码')
    routing_name: Mapped[str] = mapped_column(sa.String(150), comment='工艺路线名称')
    product_material_id: Mapped[int] = mapped_column(sa.BigInteger, comment='可生产物料 ID')
    routing_version: Mapped[str] = mapped_column(sa.String(30), comment='版本')
    routing_type: Mapped[RoutingType] = mapped_column(
        sa.String(30), default=RoutingType.STANDARD, server_default=RoutingType.STANDARD.value
    )
    base_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('1'), server_default='1')
    status: Mapped[RoutingStatus] = mapped_column(
        sa.String(20), default=RoutingStatus.DRAFT, server_default=RoutingStatus.DRAFT.value
    )
    effective_from: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    effective_to: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    is_default: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
