from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.schema.bom import (
    CalculateBomParam,
    CreateBomItemParam,
    CreateBomParam,
)
from backend.plugin.bom.service.bom_service import BomService


def test_bom_codes_are_normalized_and_created_as_draft() -> None:
    bom = CreateBomParam(
        bom_code=' bom-fg-000001-001 ',
        product_material_id=1,
        bom_version=' v1.0 ',
    )

    assert bom.bom_code == 'BOM-FG-000001-001'
    assert bom.bom_version == 'V1.0'
    assert BomStatus.DRAFT.value == 'DRAFT'


def test_bom_effective_range_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError):
        CreateBomParam(
            bom_code='BOM-1',
            product_material_id=1,
            bom_version='V1.0',
            effective_from='2026-08-02T00:00:00',
            effective_to='2026-08-01T00:00:00',
        )


def test_bom_item_defaults_to_material_unit() -> None:
    item = CreateBomItemParam(line_no=10, component_material_id=2, quantity='0.35')

    assert item.unit_id is None
    assert item.quantity == Decimal('0.35')


def test_requirement_calculation_includes_percentage_and_fixed_loss() -> None:
    item = SimpleNamespace(
        quantity=Decimal('0.35'),
        loss_rate=Decimal('2'),
        fixed_loss_qty=Decimal('5'),
        is_optional=False,
    )
    material = SimpleNamespace(id=2, material_code='RM-1', material_name='Electrolyte')
    unit = SimpleNamespace(unit_code='L')

    result = BomService._requirement(item, material, unit, Decimal('1000'), Decimal('1'))

    assert result.standard_required_qty == Decimal('350.00')
    assert result.planned_required_qty == Decimal('362.00')


def test_calculate_request_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError):
        CalculateBomParam(production_quantity=0)
