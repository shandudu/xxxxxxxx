from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, DataClassBase, TimeZone, UniversalText, id_key
from backend.plugin.inventory.enums import StockMovementStatus, StockTransactionType
from backend.utils.timezone import timezone


class InventoryBalance(Base):
    """Current inventory balance for one material, lot and physical location."""

    __tablename__ = 'mes_inventory_balance'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_inventory_balance_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_inventory_balance_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_inventory_balance_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_inventory_balance_location'),
        sa.UniqueConstraint('balance_key', name='uk_mes_inventory_balance_key'),
        sa.Index('idx_mes_inventory_balance_material', 'material_id'),
        sa.Index('idx_mes_inventory_balance_lot', 'lot_id'),
        sa.Index('idx_mes_inventory_balance_location', 'location_id'),
        {'comment': 'MES current inventory balance'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    balance_key: Mapped[str] = mapped_column(sa.String(160))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    reserved_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    version: Mapped[int] = mapped_column(default=0, server_default='0')


class StockTransaction(DataClassBase):
    """Append-only stock ledger row produced by every posted inventory operation."""

    __tablename__ = 'mes_stock_transaction'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_stock_tx_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_stock_tx_lot'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_stock_tx_warehouse'),
        sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_stock_tx_location'),
        sa.UniqueConstraint('transaction_no', name='uk_mes_stock_tx_no'),
        sa.UniqueConstraint('idempotency_key', name='uk_mes_stock_tx_idempotency'),
        sa.Index('idx_mes_stock_tx_material_time', 'material_id', 'occurred_at'),
        sa.Index('idx_mes_stock_tx_lot_time', 'lot_id', 'occurred_at'),
        sa.Index('idx_mes_stock_tx_reference', 'reference_type', 'reference_id'),
        {'comment': 'MES immutable stock transaction ledger'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    transaction_no: Mapped[str] = mapped_column(sa.String(100))
    idempotency_key: Mapped[str] = mapped_column(sa.String(180))
    transaction_type: Mapped[StockTransactionType] = mapped_column(sa.String(30))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity_delta: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    balance_after: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reference_type: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    reference_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reference_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    occurred_at: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now)


class StockMovement(Base):
    """Inventory transfer document posted exactly once."""

    __tablename__ = 'mes_stock_movement'
    __table_args__ = (
        sa.UniqueConstraint('movement_no', 'deleted', name='uk_mes_stock_movement_no_deleted'),
        sa.Index('idx_mes_stock_movement_status', 'status'),
        {'comment': 'MES stock movement document'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    movement_no: Mapped[str] = mapped_column(sa.String(100))
    status: Mapped[StockMovementStatus] = mapped_column(
        sa.String(20), default=StockMovementStatus.DRAFT, server_default=StockMovementStatus.DRAFT.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    posted_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    posted_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class StockMovementLine(Base):
    """A material and lot transfer between two physical locations."""

    __tablename__ = 'mes_stock_movement_line'
    __table_args__ = (
        sa.ForeignKeyConstraint(['movement_id'], ['mes_stock_movement.id'], name='fk_stock_movement_line_header'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_stock_movement_line_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_stock_movement_line_lot'),
        sa.ForeignKeyConstraint(['from_warehouse_id'], ['mes_warehouse.id'], name='fk_stock_movement_line_from_wh'),
        sa.ForeignKeyConstraint(['from_location_id'], ['mes_location.id'], name='fk_stock_movement_line_from_loc'),
        sa.ForeignKeyConstraint(['to_warehouse_id'], ['mes_warehouse.id'], name='fk_stock_movement_line_to_wh'),
        sa.ForeignKeyConstraint(['to_location_id'], ['mes_location.id'], name='fk_stock_movement_line_to_loc'),
        sa.UniqueConstraint('movement_id', 'line_no', 'deleted', name='uk_mes_stock_movement_line_no'),
        sa.Index('idx_mes_stock_movement_line_material', 'material_id'),
        {'comment': 'MES stock movement lines'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    movement_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    from_warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    from_location_id: Mapped[int] = mapped_column(sa.BigInteger)
    to_warehouse_id: Mapped[int] = mapped_column(sa.BigInteger)
    to_location_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
