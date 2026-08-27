import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.common.exception import errors
from backend.plugin.trace.generator.code_generator import trace_code_generator


def test_preview_renders_all_supported_business_tokens() -> None:
    result = asyncio.run(
        trace_code_generator.preview(
            '{MATERIAL}-{YYYYMMDD}-{SEQ}',
            5,
            material=SimpleNamespace(material_code='RM001'),
            now=datetime(2026, 8, 8, 10, 0, 0),
        )
    )

    assert result == 'RM001-20260808-00001'


def test_pattern_requires_sequence_token() -> None:
    with pytest.raises(errors.RequestError, match='TRACE_PATTERN_INVALID'):
        trace_code_generator.validate_pattern('{MATERIAL}-{YYYYMMDD}')


def test_pattern_rejects_unknown_token() -> None:
    with pytest.raises(errors.RequestError, match='TRACE_PATTERN_INVALID'):
        trace_code_generator.validate_pattern('{MATERIAL}-{UNKNOWN}-{SEQ}')
