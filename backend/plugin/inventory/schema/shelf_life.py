from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
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


class ShelfLifePolicyUpsert(SchemaBase):
    warning_days: int = Field(default=30, ge=1, le=3650)
    critical_days: int = Field(default=7, ge=0, le=3650)
    min_remaining_days_at_issue: int = Field(default=0, ge=0, le=3650)
    fefo_enabled: bool = True
    auto_hold_expired: bool = True
    retest_required: bool = True
    status: ShelfLifePolicyStatus = ShelfLifePolicyStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def validate_thresholds(self):
        if self.critical_days > self.warning_days:
            raise ValueError('critical_days cannot exceed warning_days')
        return self


class ShelfLifePolicyDetail(ShelfLifePolicyUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int


class ExpiryAlertDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    policy_id: int
    lot_id: int
    level: ExpiryAlertLevel
    days_remaining: int
    available_quantity: Decimal
    status: ExpiryAlertStatus
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class LotHoldDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hold_no: str
    lot_id: int
    reason: LotHoldReason
    status: LotHoldStatus
    source_type: str | None
    source_id: int | None
    source_no: str | None
    inspection_id: int | None
    original_expiry_date: datetime | None
    previous_lot_status: str | None
    previous_quality_status: str | None
    new_expiry_date: datetime | None
    held_at: datetime
    decided_at: datetime | None
    decision_reason: str | None


class ReleaseLotHold(SchemaBase):
    new_expiry_date: datetime
    decision_reason: str = Field(min_length=1, max_length=2000)


class ScrapLotHold(SchemaBase):
    decision_reason: str = Field(min_length=1, max_length=2000)


class FefoCandidateDetail(SchemaBase):
    balance_id: int
    lot_id: int
    lot_no: str
    warehouse_id: int
    location_id: int
    expiry_date: datetime
    days_remaining: int
    available_quantity: Decimal
    allocated_quantity: Decimal


class CreateLotRecall(SchemaBase):
    recall_no: str | None = Field(default=None, max_length=100)
    root_lot_id: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=4000)
    severity: str = Field(default='MAJOR', max_length=20)


class UpdateRecallItem(SchemaBase):
    status: RecallItemStatus
    action_notes: str | None = Field(default=None, max_length=2000)


class RecallItemDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recall_id: int
    item_key: str
    item_type: RecallItemType
    status: RecallItemStatus
    quantity: Decimal
    lot_id: int | None
    shipment_id: int | None
    shipment_line_id: int | None
    customer_id: int | None
    action_notes: str | None
    handled_at: datetime | None


class LotRecallDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recall_no: str
    root_lot_id: int
    reason: str
    severity: str
    status: LotRecallStatus
    initiated_at: datetime
    closed_at: datetime | None
    items: list[RecallItemDetail] = Field(default_factory=list)


class ShelfLifeDashboard(SchemaBase):
    policy_count: int
    warning_count: int
    critical_count: int
    expired_count: int
    open_hold_count: int
    active_recall_count: int
