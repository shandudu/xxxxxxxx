from decimal import Decimal
import pytest
from pydantic import ValidationError
from backend.plugin.sales.api.v1.erp.sales import router
from backend.plugin.sales.enums import SalesOrderStatus
from backend.plugin.sales.model import SalesOrder,SalesOrderDeliveryPerformance,SalesOrderLine,SalesOrderPromiseAssessment,Shipment,ShipmentLine
from backend.plugin.sales.schema.sales import CreateSalesOrder,CreateSalesOrderLine,CreateShipment,CreateShipmentLine
def test_sales_models_and_routes():
    assert [SalesOrder.__tablename__,SalesOrderLine.__tablename__,Shipment.__tablename__,ShipmentLine.__tablename__,SalesOrderPromiseAssessment.__tablename__,SalesOrderDeliveryPerformance.__tablename__]==['erp_sales_order','erp_sales_order_line','erp_shipment','erp_shipment_line','erp_sales_order_promise_assessment','erp_sales_order_delivery_performance']
    assert len(router.routes)==15
    assert '/shipments' in {r.path for r in router.routes}
    assert '/promise/dashboard' in {r.path for r in router.routes}
    assert '/promise/recalculate' in {r.path for r in router.routes}
    assert '/delivery/dashboard' in {r.path for r in router.routes}
    assert '/shipments/{shipment_id}/deliver' in {r.path for r in router.routes}
def test_sales_order_schema():
    obj=CreateSalesOrder(customer_id=1,lines=[CreateSalesOrderLine(material_id=2,ordered_quantity=Decimal('3'))]);assert obj.currency=='CNY';assert SalesOrderStatus.PARTIALLY_SHIPPED=='PARTIALLY_SHIPPED'
def test_shipment_requires_lines():
    with pytest.raises(ValidationError):CreateShipment(sales_order_id=1,lines=[])


def test_shipment_supports_fefo_and_validates_manual_allocation():
    line = CreateShipmentLine(
        sales_order_line_id=1, warehouse_id=2, quantity=Decimal('3'), auto_fefo=True,
    )
    assert line.location_id is None
    with pytest.raises(ValidationError):
        CreateShipmentLine(
            sales_order_line_id=1, warehouse_id=2, quantity=Decimal('3'),
        )
    with pytest.raises(ValidationError):
        CreateShipmentLine(
            sales_order_line_id=1, lot_id=3, warehouse_id=2,
            quantity=Decimal('3'), auto_fefo=True,
        )
