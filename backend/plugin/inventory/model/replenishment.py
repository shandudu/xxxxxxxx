from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.inventory.enums import (
    InventoryPolicyStatus,
    ReplenishmentAlertLevel,
    ReplenishmentOrderType,
    ReplenishmentStatus,
)


class InventoryPolicy(Base):
    __tablename__ = 'mes_inventory_policy'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_inventory_policy_material'),
        sa.UniqueConstraint('material_id', 'deleted', name='uk_inventory_policy_material'),
        sa.Index('idx_inventory_policy_status', 'status'),
        {'comment': 'MES material inventory safety and replenishment policy'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    safety_stock: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    reorder_point: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    max_stock: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    min_order_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    purchase_lead_days: Mapped[int] = mapped_column(sa.Integer, default=7, server_default='7')
    production_lead_days: Mapped[int] = mapped_column(sa.Integer, default=1, server_default='1')
    review_period_days: Mapped[int] = mapped_column(sa.Integer, default=7, server_default='7')
    status: Mapped[InventoryPolicyStatus] = mapped_column(
        sa.String(20), default=InventoryPolicyStatus.ACTIVE, server_default=InventoryPolicyStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class ReplenishmentSuggestion(Base):
    __tablename__ = 'mes_replenishment_suggestion'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_replenishment_material'),
        sa.ForeignKeyConstraint(['policy_id'], ['mes_inventory_policy.id'], name='fk_replenishment_policy'),
        sa.UniqueConstraint('suggestion_no', 'deleted', name='uk_replenishment_suggestion_no'),
        sa.Index('idx_replenishment_status', 'status'),
        sa.Index('idx_replenishment_material', 'material_id', 'status'),
        {'comment': 'MES automatic replenishment suggestions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    suggestion_no: Mapped[str] = mapped_column(sa.String(100))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    policy_id: Mapped[int] = mapped_column(sa.BigInteger)
    evaluated_at: Mapped[datetime] = mapped_column(TimeZone)
    due_date: Mapped[date] = mapped_column(sa.Date)
    material_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    material_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    unit_code_snapshot: Mapped[str] = mapped_column(sa.String(20))
    on_hand_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    reserved_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    open_purchase_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    open_production_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    demand_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    projected_available_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    safety_stock: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    reorder_point: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    suggested_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    order_type: Mapped[ReplenishmentOrderType] = mapped_column(sa.String(20))
    alert_level: Mapped[ReplenishmentAlertLevel] = mapped_column(sa.String(20))
    status: Mapped[ReplenishmentStatus] = mapped_column(
        sa.String(20), default=ReplenishmentStatus.SUGGESTED, server_default=ReplenishmentStatus.SUGGESTED.value
    )
    source_document_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    source_document_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_document_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    released_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
