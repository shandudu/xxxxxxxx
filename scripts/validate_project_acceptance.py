"""Run the repeatable backend acceptance suite for the ERP + MES project."""

from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, ...], ...] = (
    ('scripts/validate_project_baseline.py',),
    ('scripts/validate_route_permissions.py',),
    ('scripts/validate_mes_erp_mysql.py', '--mysql'),
    ('scripts/validate_migration_head.py',),
    ('-m', 'pytest', '-q', 'backend'),
    ('scripts/validate_manufacturing_happy_path_rollback.py',),
    ('scripts/validate_sales_order_driven_happy_path.py',),
    ('scripts/validate_sales_order_promise_rollback.py',),
    ('scripts/validate_sales_delivery_otif_rollback.py',),
    ('scripts/validate_supplier_purchase_otif_rollback.py',),
    ('scripts/validate_supplier_quality_management_rollback.py',),
    ('scripts/validate_supplier_lifecycle_rollback.py',),
    ('scripts/validate_inventory_replenishment_rollback.py',),
    ('scripts/validate_shelf_life_fefo_recall_rollback.py',),
    ('scripts/validate_trace_lot_conservation_rollback.py',),
    ('scripts/validate_maintenance_cost_freeze_rollback.py',),
    ('scripts/validate_production_andon_rollback.py',),
    ('scripts/validate_quality_nonconformance_rollback.py',),
    ('scripts/validate_quality_capa_rollback.py',),
    ('scripts/validate_quality_operation_dashboard_rollback.py',),
    ('scripts/validate_customer_rma_rollback.py',),
    ('scripts/validate_customer_after_sales_rollback.py',),
    ('scripts/validate_costing_margin_rollback.py',),
    ('scripts/validate_finance_rollback.py',),
    ('scripts/validate_finance_automation_rollback.py',),
    ('scripts/validate_finance_close_count_tax_cashflow_rollback.py',),
    ('scripts/validate_budget_cost_center_expense_rollback.py',),
    ('scripts/validate_fixed_asset_rollback.py',),
    ('scripts/validate_purchase_fixed_asset_flow_rollback.py',),
    ('scripts/validate_fixed_asset_count_dual_rollback.py',),
)


def run(command: tuple[str, ...]) -> None:
    print(f'=== {" ".join(command)} ===')
    result = subprocess.run([sys.executable, *command], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-mysql', action='store_true', help='skip the live MySQL connectivity check')
    parser.add_argument('--include-frontend', action='store_true', help='also run frontend typecheck and production build')
    args = parser.parse_args()

    for command in CHECKS:
        if args.skip_mysql and command[:1] == ('scripts/validate_mes_erp_mysql.py',):
            continue
        run(command)
    if args.include_frontend:
        frontend_root = ROOT.parent / 'fastapi-best-architecture-ui-master'
        if not frontend_root.is_dir():
            print(f'ERROR: frontend project not found: {frontend_root}')
            return 1
        pnpm = shutil.which('pnpm.cmd') or shutil.which('pnpm')
        if not pnpm:
            print('ERROR: pnpm executable not found; install pnpm or omit --include-frontend')
            return 1
        for command in ((pnpm, '-F', '@vben/web-antdv-next', 'typecheck'), (pnpm, '-F', '@vben/web-antdv-next', 'build')):
            print(f'=== {" ".join(command)} ===')
            result = subprocess.run(command, cwd=frontend_root, check=False)
            if result.returncode != 0:
                return result.returncode
    print(
        f'PROJECT_ACCEPTANCE_OK checks={len(CHECKS) - int(args.skip_mysql)} '
        f'frontend={args.include_frontend}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
