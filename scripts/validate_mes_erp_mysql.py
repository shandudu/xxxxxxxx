"""Validate the FBA MES/ERP plugin contract and, optionally, a MySQL schema.

This command is intentionally read-only.  It does not create tables, run Alembic,
seed menus, or mutate Redis.  Use it before a deployment and after migrations.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine


BUSINESS_PLUGINS = (
    'bom',
    'customer',
    'costing',
    'finance',
    'equipment',
    'inventory',
    'maintenance',
    'material',
    'operation_material',
    'performance',
    'planning',
    'production',
    'purchasing',
    'quality',
    'routing',
    'sales',
    'scheduling',
    'supplier',
    'trace',
    'warehouse',
)
REQUIRED_CORE_TABLES = {'sys_user', 'sys_role', 'sys_menu', 'sys_opera_log'}
REQUIRED_COLUMNS = {
    'mes_inventory_balance': {'version', 'balance_key'},
    'mes_stock_transaction': {'idempotency_key', 'quantity_delta'},
    'mes_production_report': {'idempotency_key', 'stock_transaction_id'},
    'mes_trace_code_sequence': {'rule_id', 'sequence_key', 'current_value'},
    'mes_shelf_life_policy': {'material_id', 'warning_days', 'critical_days', 'min_remaining_days_at_issue'},
    'mes_lot_quality_hold': {'lot_id', 'reason', 'status', 'inspection_id'},
    'mes_lot_recall_item': {'recall_id', 'item_type', 'status', 'shipment_line_id'},
    'mes_supplier_corrective_action': {'supplier_id', 'ncr_id', 'disposition_id', 'reinspection_id', 'status'},
    'mes_supplier_quality_policy': {'supplier_id', 'quality_weight', 'delivery_weight', 'conditional_score'},
    'mes_supplier_quality_assessment': {'supplier_id', 'grade', 'overall_score', 'procurement_decision'},
    'erp_supplier_qualification_application': {'supplier_id', 'status', 'valid_until'},
    'erp_supplier_qualification_audit': {'application_id', 'score', 'result'},
    'erp_supplier_sample_approval': {'application_id', 'material_id', 'status'},
    'erp_supplier_ppap_submission': {'supplier_id', 'material_id', 'status', 'expires_at'},
    'erp_supplier_approved_material': {'supplier_id', 'material_id', 'status', 'next_review_at'},
    'erp_supplier_periodic_review': {'supplier_id', 'avl_id', 'decision'},
    'mes_mold_asset': {'mold_code', 'current_shots', 'designed_life_shots', 'status'},
    'mes_mold_cavity': {'mold_id', 'cavity_no', 'status', 'defect_quantity'},
    'mes_mold_mount_record': {'mold_id', 'equipment_id', 'work_order_id', 'status'},
    'mes_mold_usage_record': {'mold_id', 'production_report_id', 'shot_count'},
    'mes_mold_maintenance_order': {'mold_id', 'maintenance_type', 'status', 'total_cost'},
    'mes_mold_cavity_quality_record': {'mold_id', 'cavity_id', 'result'},
    'mes_mold_cost_ledger': {'mold_id', 'cost_type', 'amount'},
    'mes_job_type': {'job_code', 'job_name', 'status'},
    'mes_skill_level': {'level_code', 'rank_order', 'status'},
    'mes_worker_skill': {'user_id', 'job_type_id', 'skill_level_id', 'expires_on'},
    'mes_worker_certificate': {'user_id', 'certificate_type', 'certificate_no', 'expires_on'},
    'mes_position_qualification_rule': {'job_type_id', 'minimum_skill_level_id', 'operation_id', 'work_center_id'},
    'mes_worker_authorization': {'user_id', 'job_type_id', 'work_center_id', 'effective_to'},
    'mes_worker_roster': {'user_id', 'work_date', 'shift_id', 'work_center_id'},
}
TABLE_PATTERN = re.compile(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]")
ENV_PATTERN = re.compile(r"^([A-Z0-9_]+)\s*=\s*['\"]?([^'\"\r\n]*)['\"]?\s*$")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_env(root: Path) -> dict[str, str]:
    path = root / 'backend' / '.env'
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        match = ENV_PATTERN.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def collect_model_tables(root: Path) -> set[str]:
    tables: set[str] = set()
    plugin_root = root / 'backend' / 'plugin'
    for plugin in BUSINESS_PLUGINS:
        for model_file in (plugin_root / plugin / 'model').glob('*.py'):
            tables.update(match.group(1) for match in TABLE_PATTERN.finditer(model_file.read_text(encoding='utf-8')))
    return tables


def validate_static(root: Path) -> list[str]:
    errors: list[str] = []
    plugin_root = root / 'backend' / 'plugin'
    for plugin in BUSINESS_PLUGINS:
        plugin_dir = plugin_root / plugin
        required_paths = ('plugin.toml', 'model', 'schema', 'service', 'api', 'sql/mysql/init.sql')
        missing = [path for path in required_paths if not (plugin_dir / path).exists()]
        if missing:
            errors.append(f'{plugin}: missing {", ".join(missing)}')
        else:
            config = (plugin_dir / 'plugin.toml').read_text(encoding='utf-8')
            if 'mysql' not in config:
                errors.append(f'{plugin}: plugin.toml does not declare mysql support')

    tables = collect_model_tables(root)
    missing_prefix = sorted(table for table in tables if not (table.startswith('mes_') or table.startswith('erp_')))
    if missing_prefix:
        errors.append(f'business tables without mes_/erp_ prefix: {", ".join(missing_prefix)}')
    if not tables:
        errors.append('no business plugin model tables found')
    return errors


def database_url(env: dict[str, str]) -> tuple[URL, str]:
    database = env.get('DATABASE_SCHEMA', 'fba')
    url = URL.create(
        drivername='mysql+asyncmy',
        username=env.get('DATABASE_USER', 'root'),
        password=env.get('DATABASE_PASSWORD', ''),
        host=env.get('DATABASE_HOST', '127.0.0.1'),
        port=int(env.get('DATABASE_PORT', '3306')),
        database=database,
        query={'charset': env.get('DATABASE_CHARSET', 'utf8mb4')},
    )
    return url, database


async def validate_mysql(root: Path) -> list[str]:
    env = read_env(root)
    if env.get('DATABASE_TYPE', '').lower() != 'mysql':
        return ["backend/.env DATABASE_TYPE must be 'mysql' for this check"]

    url, database = database_url(env)
    engine = create_async_engine(url, pool_pre_ping=True, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
            rows = await conn.execute(
                text(
                    'SELECT table_name FROM information_schema.tables '
                    'WHERE table_schema = :schema'
                ),
                {'schema': database},
            )
            actual_tables = {row[0] for row in rows}
            required_tables = REQUIRED_CORE_TABLES | collect_model_tables(root)
            missing_tables = sorted(required_tables - actual_tables)
            errors = [f'missing MySQL tables: {", ".join(missing_tables)}'] if missing_tables else []

            for table, required_columns in REQUIRED_COLUMNS.items():
                if table not in actual_tables:
                    continue
                columns = await conn.execute(
                    text(
                        'SELECT column_name FROM information_schema.columns '
                        'WHERE table_schema = :schema AND table_name = :table'
                    ),
                    {'schema': database, 'table': table},
                )
                actual_columns = {row[0] for row in columns}
                missing_columns = sorted(required_columns - actual_columns)
                if missing_columns:
                    errors.append(f'{table}: missing columns {", ".join(missing_columns)}')
            return errors
    except Exception as exc:  # pragma: no cover - exercised against deployment infrastructure
        return [f'MySQL connection failed: {exc.__class__.__name__}: {exc}']
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql', action='store_true', help='also connect to the configured MySQL database')
    args = parser.parse_args()

    root = project_root()
    errors = validate_static(root)
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
    else:
        print(f'OK: static plugin contract ({len(BUSINESS_PLUGINS)} plugins, {len(collect_model_tables(root))} model tables)')

    if args.mysql:
        mysql_errors = asyncio.run(validate_mysql(root))
        if mysql_errors:
            for error in mysql_errors:
                print(f'ERROR: {error}')
            errors.extend(mysql_errors)
        else:
            print('OK: MySQL connection and required schema')

    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
