from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.inventory.enums import (
    ExpiryAlertLevel,
    ExpiryAlertStatus,
    LotHoldReason,
    LotHoldStatus,
    LotRecallStatus,
    RecallItemStatus,
    RecallItemType,
    ShelfLifePolicyStatus,
)


class ShelfLifePolicy(Base):
    __tablename__ = 'mes_shelf_life_policy'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_shelf_life_policy_material'),
        sa.UniqueConstraint('material_id', 'deleted', name='uk_shelf_life_policy_material'),
        sa.Index('idx_shelf_life_policy_status', 'status'),
        {'comment': 'Material shelf-life warning and FEFO policy'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    warning_days: Mapped[int] = mapped_column(sa.Integer, default=30, server_default='30')
    critical_days: Mapped[int] = mapped_column(sa.Integer, default=7, server_default='7')
    min_remaining_days_at_issue: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    fefo_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    auto_hold_expired: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    retest_required: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    status: Mapped[ShelfLifePolicyStatus] = mapped_column(
        sa.String(20), default=ShelfLifePolicyStatus.ACTIVE, server_default=ShelfLifePolicyStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class LotExpiryAlert(Base):
    __tablename__ = 'mes_lot_expiry_alert'
    __table_args__ = (
        sa.ForeignKeyConstraint(['policy_id'], ['mes_shelf_life_policy.id'], name='fk_expiry_alert_policy'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_expiry_alert_lot'),
        sa.UniqueConstraint('lot_id', 'deleted', name='uk_expiry_alert_lot'),
        sa.Index('idx_expiry_alert_status_level', 'status', 'level'),
        {'comment': 'Material lot shelf-life warning'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    policy_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int] = mapped_column(sa.BigInteger)
    level: Mapped[ExpiryAlertLevel] = mapped_column(sa.String(20))
    days_remaining: Mapped[int] = mapped_column(sa.Integer)
    triggered_at: Mapped[datetime] = mapped_column(TimeZone)
    available_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[ExpiryAlertStatus] = mapped_column(
        sa.String(20), default=ExpiryAlertStatus.OPEN, server_default=ExpiryAlertStatus.OPEN.value
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    acknowledged_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)


class LotQualityHold(Base):
    __tablename__ = 'mes_lot_quality_hold'
    __table_args__ = (
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_lot_quality_hold_lot'),
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_lot_quality_hold_inspection'),
        sa.UniqueConstraint('hold_no', 'deleted', name='uk_lot_quality_hold_no'),
        sa.Index('idx_lot_quality_hold_lot_status', 'lot_id', 'status'),
        {'comment': 'Lot quality isolation and disposition'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    hold_no: Mapped[str] = mapped_column(sa.String(100))
    lot_id: Mapped[int] = mapped_column(sa.BigInteger)
    reason: Mapped[LotHoldReason] = mapped_column(sa.String(30))
    held_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[LotHoldStatus] = mapped_column(
        sa.String(30), default=LotHoldStatus.OPEN, server_default=LotHoldStatus.OPEN.value
    )
    source_type: Mapped[str | None] = mapped_column(sa.String(40), default=None)
    source_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    inspection_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    original_expiry_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    previous_lot_status: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    previous_quality_status: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    new_expiry_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    decided_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    decision_reason: Mapped[str | None] = mapped_column(UniversalText, default=None)


class LotRecall(Base):
    __tablename__ = 'mes_lot_recall'
    __table_args__ = (
        sa.ForeignKeyConstraint(['root_lot_id'], ['mes_material_lot.id'], name='fk_lot_recall_root_lot'),
        sa.UniqueConstraint('recall_no', 'deleted', name='uk_lot_recall_no'),
        sa.Index('idx_lot_recall_status', 'status'),
        {'comment': 'Lot recall case'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    recall_no: Mapped[str] = mapped_column(sa.String(100))
    root_lot_id: Mapped[int] = mapped_column(sa.BigInteger)
    reason: Mapped[str] = mapped_column(UniversalText)
    initiated_at: Mapped[datetime] = mapped_column(TimeZone)
    severity: Mapped[str] = mapped_column(sa.String(20), default='MAJOR', server_default='MAJOR')
    status: Mapped[LotRecallStatus] = mapped_column(
        sa.String(20), default=LotRecallStatus.ACTIVE, server_default=LotRecallStatus.ACTIVE.value
    )
    closed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    initiated_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    closed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class LotRecallItem(Base):
    __tablename__ = 'mes_lot_recall_item'
    __table_args__ = (
        sa.ForeignKeyConstraint(['recall_id'], ['mes_lot_recall.id'], name='fk_lot_recall_item_recall'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_lot_recall_item_lot'),
        sa.ForeignKeyConstraint(['shipment_id'], ['erp_shipment.id'], name='fk_lot_recall_item_shipment'),
        sa.ForeignKeyConstraint(['shipment_line_id'], ['erp_shipment_line.id'], name='fk_lot_recall_item_shipment_line'),
        sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_lot_recall_item_customer'),
        sa.UniqueConstraint('recall_id', 'item_key', 'deleted', name='uk_lot_recall_item_key'),
        sa.Index('idx_lot_recall_item_status', 'recall_id', 'status'),
        {'comment': 'Affected inventory and customer shipment in a lot recall'},
    )
    id: Mapped[id_key] = mapped_column(init=False)
    recall_id: Mapped[int] = mapped_column(sa.BigInteger)
    item_key: Mapped[str] = mapped_column(sa.String(160))
    item_type: Mapped[RecallItemType] = mapped_column(sa.String(30))
    status: Mapped[RecallItemStatus] = mapped_column(sa.String(30))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    shipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    shipment_line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    customer_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    action_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
    handled_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    handled_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
