"""Validate the repository-level ERP/MES delivery baseline without external services.

This check intentionally stays static so it can run on a developer workstation
before MySQL/Redis/RabbitMQ are started. Runtime database checks remain covered
by ``validate_mes_erp_mysql.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_BACKEND_PLUGINS = {
    'bom',
    'customer',
    'costing',
    'finance',
    'equipment',
    'inventory',
    'maintenance',
    'material',
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
}

REQUIRED_DOCS = {
    'docs/ERP_MES_PROJECT_MASTER_PLAN_V1.0.md',
    'docs/SALES_ORDER_ATP_CTP_PROMISE_PRD_V1.0.md',
    'docs/MRP_NET_REQUIREMENT_ACTION_PRD_V1.0.md',
    'docs/SALES_ORDER_DELIVERY_OTIF_PRD_V1.0.md',
    'docs/SUPPLIER_PURCHASE_OTIF_IMPACT_PRD_V1.0.md',
    'docs/ALERT_CENTER_PRD_V1.0.md',
    'docs/PRODUCTION_COST_ACCOUNTING_MARGIN_PRD_V1.0.md',
    'docs/INVENTORY_FINANCE_AR_AP_PROFIT_PRD_V1.0.md',
    'docs/FINANCE_AUTOMATION_INVOICE_MATCH_BANK_PRD_V1.0.md',
    'docs/FINANCE_CLOSE_COUNT_TAX_CASHFLOW_PRD_V1.0.md',
    'docs/BUDGET_COST_CENTER_EXPENSE_PRD_V1.0.md',
    'docs/FIXED_ASSET_LIFECYCLE_DEPRECIATION_PRD_V1.0.md',
    'docs/PURCHASE_RECEIPT_FIXED_ASSET_MATCHING_PRD_V1.0.md',
    'docs/FIXED_ASSET_COUNT_BARCODE_DUAL_DEPRECIATION_PRD_V1.0.md',
}


def check_paths() -> list[str]:
    errors: list[str] = []
    plugin_root = ROOT / 'backend' / 'plugin'
    missing_plugins = sorted(name for name in REQUIRED_BACKEND_PLUGINS if not (plugin_root / name).is_dir())
    if missing_plugins:
        errors.append(f'missing backend plugins: {", ".join(missing_plugins)}')

    missing_docs = sorted(path for path in REQUIRED_DOCS if not (ROOT / path).is_file())
    if missing_docs:
        errors.append(f'missing delivery docs: {", ".join(missing_docs)}')

    for path in (
        'backend/alembic',
        'scripts/validate_mes_erp_mysql.py',
        'scripts/validate_migration_head.py',
        'scripts/validate_manufacturing_happy_path_rollback.py',
        'scripts/validate_route_permissions.py',
        'scripts/validate_project_acceptance.py',
        'scripts/validate_costing_margin_rollback.py',
        'scripts/validate_finance_rollback.py',
        'scripts/validate_finance_automation_rollback.py',
        'scripts/validate_finance_close_count_tax_cashflow_rollback.py',
        'scripts/validate_budget_cost_center_expense_rollback.py',
        'scripts/validate_fixed_asset_rollback.py',
        'scripts/validate_purchase_fixed_asset_flow_rollback.py',
        'scripts/validate_fixed_asset_count_dual_rollback.py',
        'docker-compose.yml',
    ):
        if not (ROOT / path).exists():
            errors.append(f'missing required path: {path}')
    return errors


def check_mysql_compose() -> list[str]:
    errors: list[str] = []
    compose = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    if 'fba_mysql:' not in compose or 'image: mysql:8.0.41' not in compose:
        errors.append('docker-compose.yml must define the MySQL 8 service fba_mysql')
    if 'fba_postgres:' in compose or 'image: postgres:' in compose:
        errors.append('docker-compose.yml still contains an active PostgreSQL service')
    if 'wait-for-it -s fba_mysql:3306' not in compose:
        errors.append('fba_server must wait for fba_mysql:3306')
    env_file = ROOT / 'deploy' / 'backend' / 'docker-compose' / '.env.server'
    env_text = env_file.read_text(encoding='utf-8')
    if "MYSQL_HOST='fba_mysql'" not in env_text:
        errors.append('.env.server must use MYSQL_HOST=fba_mysql inside Compose')
    if "REDIS_HOST='fba_redis'" not in env_text:
        errors.append('.env.server must use REDIS_HOST=fba_redis inside Compose')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate the ERP/MES project delivery baseline')
    parser.add_argument('--quiet', action='store_true', help='only print failures')
    args = parser.parse_args()

    errors = [*check_paths(), *check_mysql_compose()]
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        return 1

    if not args.quiet:
        print(f'OK: project baseline ({len(REQUIRED_BACKEND_PLUGINS)} backend business plugins)')
        print(f'OK: delivery docs ({len(REQUIRED_DOCS)} required PRD/plan files)')
        print('OK: Docker Compose uses MySQL 8 on port 3306')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
