import pytest

from backend.plugin.supplier.schema.supplier import (
    CreateSupplierMaterialParam,
    CreateSupplierParam,
)


def _supplier_data() -> dict:
    return {
        'supplier_code': ' sup-001 ',
        'supplier_name': ' Demo Supplier ',
        'category_id': 1,
        'supplier_type': 'MATERIAL',
        'company_type': 'COMPANY',
    }


def test_supplier_code_is_trimmed_and_uppercased() -> None:
    supplier = CreateSupplierParam(**_supplier_data())

    assert supplier.supplier_code == 'SUP-001'
    assert supplier.supplier_name == 'Demo Supplier'


def test_supplier_keeps_operational_quality_and_cooperation_states_independent() -> None:
    supplier = CreateSupplierParam(
        **_supplier_data(),
        status='DISABLED',
        cooperation_status='BLACKLISTED',
        quality_status='CONDITIONAL',
    )

    assert supplier.status == 'DISABLED'
    assert supplier.cooperation_status == 'BLACKLISTED'
    assert supplier.quality_status == 'CONDITIONAL'


def test_supplier_material_accepts_six_decimal_places() -> None:
    relation = CreateSupplierMaterialParam(material_id=1, minimum_order_quantity='1.234567')

    assert str(relation.minimum_order_quantity) == '1.234567'


def test_supplier_material_rejects_negative_moq() -> None:
    with pytest.raises(ValueError):
        CreateSupplierMaterialParam(material_id=1, minimum_order_quantity='-0.000001')
