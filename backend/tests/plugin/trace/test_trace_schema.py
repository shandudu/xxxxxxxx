from decimal import Decimal

import pytest

from backend.common.model import MappedBase
from backend.plugin.trace.schema.trace import (
    CreateMaterialLotParam,
    CreateTraceCodeRuleParam,
    LotSplitParam,
)


def test_rule_code_is_normalized_and_pattern_is_preserved() -> None:
    rule = CreateTraceCodeRuleParam(
        rule_code=' lot-daily ',
        rule_name='Daily lot',
        rule_type='LOT',
        pattern='{MATERIAL}-{YYYYMMDD}-{SEQ}',
    )

    assert rule.rule_code == 'LOT-DAILY'
    assert rule.pattern == '{MATERIAL}-{YYYYMMDD}-{SEQ}'


def test_manual_lot_requires_lot_number() -> None:
    with pytest.raises(ValueError):
        CreateMaterialLotParam(material_id=1, generate_by_rule=False)


def test_lot_split_rejects_duplicate_child_codes() -> None:
    with pytest.raises(ValueError):
        LotSplitParam(
            children=[
                {'lot_no': 'LOT-A-01', 'quantity': Decimal('1')},
                {'lot_no': 'LOT-A-01', 'quantity': Decimal('2')},
            ]
        )


def test_trace_schema_registers_all_persistent_tables() -> None:
    expected = {
        'mes_trace_code_rule',
        'mes_trace_code_sequence',
        'mes_material_trace_rule',
        'mes_material_lot',
        'mes_material_serial',
        'mes_trace_relation',
        'mes_trace_operation_log',
    }

    assert expected.issubset(MappedBase.metadata.tables)
