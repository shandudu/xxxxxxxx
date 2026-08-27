import pytest

from backend.plugin.material.schema.material import CreateMaterialParam, CreateUnitParam


def test_material_code_is_trimmed_and_uppercased() -> None:
    material = CreateMaterialParam(
        material_code=' rm-000001 ',
        material_name='铜箔',
        material_type='RAW_MATERIAL',
        category_id=1,
        base_unit_id=2,
    )

    assert material.material_code == 'RM-000001'


def test_material_code_rejects_unsupported_characters() -> None:
    with pytest.raises(ValueError):
        CreateMaterialParam(
            material_code='RM/000001',
            material_name='铜箔',
            material_type='RAW_MATERIAL',
            category_id=1,
            base_unit_id=2,
        )


def test_material_keeps_batch_and_serial_controls_independent() -> None:
    material = CreateMaterialParam(
        material_code='FG-000001',
        material_name='电芯',
        material_type='FINISHED_PRODUCT',
        category_id=3,
        base_unit_id=1,
        batch_control=True,
        serial_control=True,
        shelf_life_days=365,
    )

    assert material.batch_control is True
    assert material.serial_control is True
    assert material.shelf_life_days == 365


def test_negative_shelf_life_is_rejected() -> None:
    with pytest.raises(ValueError):
        CreateMaterialParam(
            material_code='RM-000001',
            material_name='铜箔',
            material_type='RAW_MATERIAL',
            category_id=1,
            base_unit_id=2,
            shelf_life_days=-1,
        )


def test_unit_code_is_normalized() -> None:
    unit = CreateUnitParam(unit_code=' kg ', unit_name='千克', decimal_places=3)

    assert unit.unit_code == 'KG'
