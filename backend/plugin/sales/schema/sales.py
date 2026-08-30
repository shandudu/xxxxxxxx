from datetime import datetime
from decimal import Decimal
from pydantic import ConfigDict,Field,model_validator
from backend.common.schema import SchemaBase
from backend.plugin.sales.enums import SalesOrderStatus
class CreateSalesOrderLine(SchemaBase):
    material_id:int=Field(ge=1);ordered_quantity:Decimal=Field(gt=0,max_digits=18,decimal_places=6);unit_price:Decimal|None=Field(default=None,ge=0)
class CreateSalesOrder(SchemaBase):
    sales_order_no:str|None=Field(default=None,max_length=100);customer_id:int=Field(ge=1);currency:str=Field(default='CNY',max_length=10);requested_delivery_at:datetime|None=None;remark:str|None=Field(default=None,max_length=500);lines:list[CreateSalesOrderLine]=Field(min_length=1,max_length=500)
class SalesOrderLineDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;line_no:int;material_id:int;unit_id:int;material_code_snapshot:str;material_name_snapshot:str;unit_code_snapshot:str;ordered_quantity:Decimal;shipped_quantity:Decimal;unit_price:Decimal|None
class SalesOrderDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;sales_order_no:str;customer_id:int;customer_code_snapshot:str;customer_name_snapshot:str;status:SalesOrderStatus;currency:str;requested_delivery_at:datetime|None;remark:str|None;created_time:datetime;lines:list[SalesOrderLineDetail]=Field(default_factory=list)
class CreateShipmentLine(SchemaBase):
    sales_order_line_id:int=Field(ge=1);lot_id:int|None=Field(default=None,ge=1);warehouse_id:int=Field(ge=1);location_id:int|None=Field(default=None,ge=1);quantity:Decimal=Field(gt=0,max_digits=18,decimal_places=6);auto_fefo:bool=False
    @model_validator(mode='after')
    def validate_allocation(self):
        if self.auto_fefo and self.lot_id is not None:raise ValueError('auto FEFO cannot specify lot_id')
        if not self.auto_fefo and self.location_id is None:raise ValueError('manual shipment requires location_id')
        return self
class CreateShipment(SchemaBase):
    shipment_no:str|None=Field(default=None,max_length=100);sales_order_id:int=Field(ge=1);remark:str|None=Field(default=None,max_length=500);lines:list[CreateShipmentLine]=Field(min_length=1,max_length=500)
class ShipmentLineDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;sales_order_line_id:int;material_id:int;lot_id:int|None;warehouse_id:int;location_id:int;quantity:Decimal;stock_transaction_id:int;lot_no_snapshot:str|None
class ShipmentDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;shipment_no:str;sales_order_id:int;customer_id:int;customer_code_snapshot:str;customer_name_snapshot:str;status:str;delivered_at:datetime|None;remark:str|None;created_time:datetime;lines:list[ShipmentLineDetail]=Field(default_factory=list)
class DeliverShipment(SchemaBase):
    delivered_at:datetime|None=None


class PromiseAssessmentDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True)
    id: int
    sales_order_id: int
    sales_order_line_id: int
    material_id: int
    requested_delivery_at: datetime
    assessed_at: datetime
    ordered_quantity: Decimal
    shipped_quantity: Decimal
    atp_quantity: Decimal
    open_purchase_quantity: Decimal
    open_production_quantity: Decimal
    ctp_quantity: Decimal
    shortage_quantity: Decimal
    capacity_shortage_quantity: Decimal
    promised_delivery_at: datetime | None
    risk_status: str
    risk_notes: str | None


class PromiseDashboard(SchemaBase):
    risk_counts: dict[str, int]
    order_count: int
    delayed_order_count: int
    total_shortage_quantity: Decimal
    total_capacity_shortage_quantity: Decimal


class PromiseRecalculateResult(SchemaBase):
    assessed_order_count: int
    assessed_line_count: int
    assessed_at: datetime

class DeliveryPerformanceDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True)
    id:int; sales_order_id:int; sales_order_line_id:int; material_id:int; promised_delivery_at:datetime; actual_delivery_at:datetime|None; assessed_at:datetime; ordered_quantity:Decimal; shipped_quantity:Decimal; on_time:bool; in_full:bool; otif_status:str; delay_reason:str|None; last_shipment_id:int|None

class DeliveryDashboard(SchemaBase):
    order_count:int; completed_order_count:int; in_transit_order_count:int; delayed_order_count:int; line_count:int; otif_line_count:int; on_time_line_count:int; in_full_line_count:int; otif_rate:Decimal; on_time_rate:Decimal; in_full_rate:Decimal; delay_reasons:dict[str,int]

class DeliveryRecalculateResult(SchemaBase):
    assessed_order_count:int; assessed_line_count:int; assessed_at:datetime
