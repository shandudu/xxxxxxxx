from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.purchasing.enums import PurchaseOrderStatus, SupplierReceiptStatus


class CreatePurchaseOrderLine(SchemaBase):
    material_id: int = Field(ge=1)
    ordered_quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    requested_delivery_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)


class CreatePurchaseOrder(SchemaBase):
    purchase_order_no: str | None = Field(default=None, max_length=100)
    supplier_id: int = Field(ge=1)
    currency: str = Field(default='CNY', min_length=3, max_length=10)
    remark: str | None = Field(default=None, max_length=500)
    lines: list[CreatePurchaseOrderLine] = Field(min_length=1, max_length=500)


class PurchaseOrderLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    line_no: int
    material_id: int
    unit_id: int
    ordered_quantity: Decimal
    received_quantity: Decimal
    unit_price: Decimal | None
    material_code_snapshot: str
    material_name_snapshot: str
    unit_code_snapshot: str
    unit_name_snapshot: str
    requested_delivery_at: datetime | None
    supplier_confirmed_delivery_at: datetime | None
    remark: str | None


class PurchaseOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_no: str
    supplier_id: int
    supplier_code_snapshot: str
    supplier_name_snapshot: str
    status: PurchaseOrderStatus
    currency: str
    remark: str | None
    created_time: datetime
    updated_time: datetime | None = None
    lines: list[PurchaseOrderLineDetail] = Field(default_factory=list)


class CreateSupplierReceiptLine(SchemaBase):
    purchase_order_line_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)
    location_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    lot_id: int | None = Field(default=None, ge=1)
    lot_no: str | None = Field(default=None, max_length=100)
    supplier_lot_no: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_lot_input(self):
        if self.lot_id is not None and self.lot_no:
            raise ValueError('lot_id and lot_no cannot both be supplied')
        return self


class CreateSupplierReceipt(SchemaBase):
    receipt_no: str | None = Field(default=None, max_length=100)
    purchase_order_id: int = Field(ge=1)
    remark: str | None = Field(default=None, max_length=500)
    lines: list[CreateSupplierReceiptLine] = Field(min_length=1, max_length=500)


class ConfirmPurchaseOrder(SchemaBase):
    supplier_confirmed_delivery_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=500)


class SupplierReceiptLineDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_receipt_id: int
    purchase_order_line_id: int
    line_no: int
    material_id: int
    lot_id: int | None
    warehouse_id: int
    location_id: int
    quantity: Decimal
    material_code_snapshot: str
    material_name_snapshot: str
    lot_no_snapshot: str | None
    warehouse_code_snapshot: str
    location_code_snapshot: str
    stock_transaction_id: int
    remark: str | None


class SupplierReceiptDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_no: str
    purchase_order_id: int
    supplier_id: int
    supplier_code_snapshot: str
    supplier_name_snapshot: str
    status: SupplierReceiptStatus
    remark: str | None
    created_time: datetime
    lines: list[SupplierReceiptLineDetail] = Field(default_factory=list)


class SupplierReturnDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    return_no: str
    supplier_id: int
    supplier_receipt_id: int
    ncr_id: int
    disposition_id: int
    supplier_code_snapshot: str
    supplier_name_snapshot: str
    status: str
    remark: str | None
    created_time: datetime


class PurchaseDeliveryPerformanceDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int
    purchase_order_id: int
    purchase_order_line_id: int
    material_id: int
    requested_delivery_at: datetime
    supplier_confirmed_delivery_at: datetime | None
    effective_delivery_at: datetime
    assessed_at: datetime
    ordered_quantity: Decimal
    actual_delivery_at: datetime | None
    received_quantity: Decimal
    on_time: bool
    in_full: bool
    otif_status: str
    delay_reason: str | None
    days_late: int
    shortage_impact_quantity: Decimal
    impacted_sales_order_count: int
    mrp_uncovered_quantity: Decimal


class PurchaseDeliveryDashboard(SchemaBase):
    order_count: int
    supplier_count: int
    line_count: int
    otif_line_count: int
    delayed_line_count: int
    otif_rate: Decimal
    delayed_quantity: Decimal
    shortage_impact_quantity: Decimal
    impacted_sales_order_count: int
    supplier_otif: list[dict[str, object]] = Field(default_factory=list)


class PurchaseDeliveryRecalculateResult(SchemaBase):
    assessed_order_count: int
    assessed_line_count: int
    assessed_at: datetime
