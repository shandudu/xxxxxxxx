"""Scope repair-part idempotency keys to one repair order."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'j0e3f5a7b9c1'
down_revision: str | None = 'i9d2e4f6a8b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _unique_columns() -> dict[str, tuple[str, ...]]:
    inspector = sa.inspect(op.get_bind())
    if 'mes_repair_part_issue' not in inspector.get_table_names():
        return {}
    return {
        item['name']: tuple(item['column_names'])
        for item in inspector.get_unique_constraints('mes_repair_part_issue')
        if item.get('name')
    }


def upgrade() -> None:
    constraints = _unique_columns()
    current = constraints.get('uk_repair_part_issue_idempotency')
    if current == ('idempotency_key', 'deleted'):
        op.drop_constraint(
            'uk_repair_part_issue_idempotency',
            'mes_repair_part_issue',
            type_='unique',
        )
    if current != ('repair_id', 'idempotency_key', 'deleted'):
        op.create_unique_constraint(
            'uk_repair_part_issue_idempotency',
            'mes_repair_part_issue',
            ['repair_id', 'idempotency_key', 'deleted'],
        )


def downgrade() -> None:
    constraints = _unique_columns()
    current = constraints.get('uk_repair_part_issue_idempotency')
    if current == ('repair_id', 'idempotency_key', 'deleted'):
        op.drop_constraint(
            'uk_repair_part_issue_idempotency',
            'mes_repair_part_issue',
            type_='unique',
        )
    if current != ('idempotency_key', 'deleted'):
        op.create_unique_constraint(
            'uk_repair_part_issue_idempotency',
            'mes_repair_part_issue',
            ['idempotency_key', 'deleted'],
        )
