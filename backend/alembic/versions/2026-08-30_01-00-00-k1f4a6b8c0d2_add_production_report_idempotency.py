"""Add work-order scoped idempotency keys to production reports."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'k1f4a6b8c0d2'
down_revision: str | None = 'j0e3f5a7b9c1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if 'mes_production_report' not in inspector.get_table_names():
        return set()
    return {item['name'] for item in inspector.get_columns('mes_production_report')}


def _unique_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if 'mes_production_report' not in inspector.get_table_names():
        return set()
    return {
        item['name']
        for item in inspector.get_unique_constraints('mes_production_report')
        if item.get('name')
    }


def _index_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if 'mes_production_report' not in inspector.get_table_names():
        return set()
    return {item['name'] for item in inspector.get_indexes('mes_production_report')}


def upgrade() -> None:
    if 'idempotency_key' not in _columns():
        op.add_column(
            'mes_production_report',
            sa.Column('idempotency_key', sa.String(length=180), nullable=True),
        )
    if 'idx_mes_production_report_work_order' not in _index_names():
        op.create_index(
            'idx_mes_production_report_work_order',
            'mes_production_report',
            ['work_order_id'],
        )
    if 'uk_mes_production_report_idempotency' not in _unique_names():
        op.create_unique_constraint(
            'uk_mes_production_report_idempotency',
            'mes_production_report',
            ['work_order_id', 'idempotency_key', 'deleted'],
        )


def downgrade() -> None:
    # MySQL may choose the composite unique index to support the work-order FK.
    # Keep an explicit single-column index before removing that unique index.
    if 'idx_mes_production_report_work_order' not in _index_names():
        op.create_index(
            'idx_mes_production_report_work_order',
            'mes_production_report',
            ['work_order_id'],
        )
    if 'uk_mes_production_report_idempotency' in _unique_names():
        op.drop_constraint(
            'uk_mes_production_report_idempotency',
            'mes_production_report',
            type_='unique',
        )
    if 'idempotency_key' in _columns():
        op.drop_column('mes_production_report', 'idempotency_key')
