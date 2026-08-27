from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.purchasing.api.v1.erp.purchasing import router
from backend.plugin.purchasing.enums import PurchaseOrderStatus
from backend.plugin.purchasing.model import PurchaseOrder, PurchaseOrderDeliveryPerformance, PurchaseOrderLine, SupplierReceipt, SupplierReceiptLine, SupplierReturn, SupplierReturnLine
from backend.plugin.purchasing.schema.purchasing import CreatePurchaseOrder, CreatePurchaseOrderLine, CreateSupplierReceiptLine


def test_purchasing_models_registered() -> None:
    assert PurchaseOrder.__tablename__ == 'erp_purchase_order'
    assert PurchaseOrderLine.__tablename__ == 'erp_purchase_order_line'
    assert SupplierReceipt.__tablename__ == 'erp_supplier_receipt'
    assert SupplierReceiptLine.__tablename__ == 'erp_supplier_receipt_line'
    assert SupplierReturn.__tablename__ == 'erp_supplier_return'
    assert SupplierReturnLine.__tablename__ == 'erp_supplier_return_line'
    assert PurchaseOrderDeliveryPerformance.__tablename__ == 'erp_purchase_order_delivery_performance'
    assert 'uk_erp_purchase_order_no_deleted' in {item.name for item in PurchaseOrder.__table__.constraints}


def test_purchasing_route_surface() -> None:
    assert {route.path for route in router.routes} == {
        '/orders', '/orders/{order_id}', '/orders/{order_id}/confirm', '/orders/{order_id}/cancel',
        '/receipts', '/receipts/{receipt_id}', '/returns', '/delivery/dashboard', '/delivery/recalculate', '/orders/{order_id}/delivery-performance',
    }
    assert len(router.routes) == 12


def test_purchase_order_schema() -> None:
    order = CreatePurchaseOrder(
        supplier_id=1,
        lines=[CreatePurchaseOrderLine(material_id=2, ordered_quantity=Decimal('12.5'))],
    )
    assert order.currency == 'CNY'
    assert order.lines[0].ordered_quantity == Decimal('12.5')
    assert PurchaseOrderStatus.PARTIALLY_RECEIVED == 'PARTIALLY_RECEIVED'


def test_receipt_line_rejects_conflicting_lot_inputs() -> None:
    with pytest.raises(ValidationError):
        CreateSupplierReceiptLine(
            purchase_order_line_id=1, warehouse_id=1, location_id=1,
            quantity=Decimal('1'), lot_id=2, lot_no='LOT-001',
        )
