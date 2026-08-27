import pytest

from backend.plugin.warehouse.schema.warehouse import (
    LocationGenerateConfig,
    LocationRangeConfig,
    CreateWarehouseConfig,
)


def test_codes_are_normalized_to_uppercase() -> None:
    warehouse = CreateWarehouseConfig(
        warehouse_code=' rm01 ',
        warehouse_name='原材料仓',
        warehouse_type='RAW_MATERIAL',
    )

    assert warehouse.warehouse_code == 'RM01'


def test_location_range_rejects_reversed_range() -> None:
    with pytest.raises(ValueError):
        LocationRangeConfig(start=10, end=1, digits=2)


def test_location_generate_config_accepts_default_pattern() -> None:
    config = LocationGenerateConfig(
        warehouse_id=1,
        area_id=2,
        area_prefix='a',
        rack={'start': 1, 'end': 2, 'digits': 2},
        level={'start': 1, 'end': 2, 'digits': 2},
        bin={'start': 1, 'end': 2, 'digits': 2},
    )

    assert config.area_prefix == 'A'
    assert config.pattern == '{AREA}{RACK}-{LEVEL}-{BIN}'

