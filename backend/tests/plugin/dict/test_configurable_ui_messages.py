from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MIGRATION = ROOT / 'backend' / 'alembic' / 'versions' / '2026-09-05_02-00-00-r8m1h3i5j7k9_seed_configurable_ui_messages.py'
MIGRATED_VIEWS = (
    'frontend/apps/web-antdv-next/src/plugins/maintenance/views/index.vue',
    'frontend/apps/web-antdv-next/src/plugins/inventory/views/replenishment.vue',
    'frontend/apps/web-antdv-next/src/plugins/inventory/views/shelf-life.vue',
    'frontend/apps/web-antdv-next/src/plugins/supplier/views/lifecycle.vue',
    'frontend/apps/web-antdv-next/src/plugins/quality/views/sqm.vue',
    'frontend/apps/web-antdv-next/src/plugins/equipment/views/molds.vue',
)


def _migration_module():
    spec = importlib.util.spec_from_file_location('configurable_ui_messages_migration', MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seeded_message_keys_and_parameters_are_stable() -> None:
    module = _migration_module()
    identities = [(type_code, value) for type_code, value, _zh, _en in module.MESSAGES]
    assert len(identities) == len(set(identities))
    assert all(len(type_code) <= 32 and len(value) <= 128 for type_code, value in identities)
    for _type_code, _value, zh, en in module.MESSAGES:
        assert set(re.findall(r'\{([^{}]+)\}', zh)) == set(re.findall(r'\{([^{}]+)\}', en))


def test_migrated_workflows_do_not_embed_chinese_ant_messages() -> None:
    message_call = re.compile(r'message\.(?:success|warning|error|info)\([^\n]*[\u3400-\u9fff]')
    for relative_path in MIGRATED_VIEWS:
        source = (ROOT / relative_path).read_text(encoding='utf-8')
        assert not message_call.search(source), relative_path
