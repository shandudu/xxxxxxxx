"""Add repair spare-part issue, cost posting and downtime analysis tables."""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'i9d2e4f6a8b0'
down_revision: str | None = 'h8c1d3e5f7a9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def base() -> list[sa.Column]:
    return [sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False), sa.Column('created_time', sa.DateTime(timezone=True), nullable=False), sa.Column('updated_time', sa.DateTime(timezone=True), nullable=True), sa.Column('deleted', sa.BigInteger(), server_default='0', nullable=False), sa.Column('deleted_time', sa.DateTime(timezone=True), nullable=True), sa.PrimaryKeyConstraint('id')]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if 'mes_repair_part_issue' not in tables:
        op.create_table('mes_repair_part_issue',
            sa.Column('repair_id', sa.BigInteger(), nullable=False), sa.Column('material_id', sa.BigInteger(), nullable=False), sa.Column('lot_id', sa.BigInteger(), nullable=True), sa.Column('warehouse_id', sa.BigInteger(), nullable=False), sa.Column('location_id', sa.BigInteger(), nullable=False), sa.Column('quantity', sa.Numeric(18, 6), nullable=False), sa.Column('unit_cost', sa.Numeric(18, 6), server_default='0', nullable=False), sa.Column('total_cost', sa.Numeric(18, 6), server_default='0', nullable=False), sa.Column('idempotency_key', sa.String(180), nullable=False), sa.Column('stock_transaction_id', sa.BigInteger(), nullable=True), sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False), sa.Column('remark', sa.Text(), nullable=True), *base(),
            sa.ForeignKeyConstraint(['repair_id'], ['mes_repair_order.id'], name='fk_repair_part_issue_repair'), sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_repair_part_issue_material'), sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_repair_part_issue_lot'), sa.ForeignKeyConstraint(['warehouse_id'], ['mes_warehouse.id'], name='fk_repair_part_issue_warehouse'), sa.ForeignKeyConstraint(['location_id'], ['mes_location.id'], name='fk_repair_part_issue_location'), sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_repair_part_issue_idempotency'), comment='MES repair spare-part issues linked to inventory transactions')
        op.create_index('ix_mes_repair_part_issue_id', 'mes_repair_part_issue', ['id'], unique=True); op.create_index('idx_repair_part_issue_repair', 'mes_repair_part_issue', ['repair_id', 'issued_at'])
    if 'mes_repair_cost_posting' not in tables:
        op.create_table('mes_repair_cost_posting',
            sa.Column('repair_id', sa.BigInteger(), nullable=False), sa.Column('period_id', sa.BigInteger(), nullable=False), sa.Column('parts_cost', sa.Numeric(18, 6), server_default='0', nullable=False), sa.Column('labor_cost', sa.Numeric(18, 6), server_default='0', nullable=False), sa.Column('total_cost', sa.Numeric(18, 6), server_default='0', nullable=False), sa.Column('voucher_id', sa.BigInteger(), nullable=True), sa.Column('posted_at', sa.DateTime(timezone=True), nullable=False), sa.Column('remark', sa.Text(), nullable=True), *base(),
            sa.ForeignKeyConstraint(['repair_id'], ['mes_repair_order.id'], name='fk_repair_cost_posting_repair'), sa.ForeignKeyConstraint(['period_id'], ['erp_finance_period.id'], name='fk_repair_cost_posting_period'), sa.ForeignKeyConstraint(['voucher_id'], ['erp_gl_voucher.id'], name='fk_repair_cost_posting_voucher'), sa.UniqueConstraint('repair_id', 'deleted', name='uk_repair_cost_posting_repair'), comment='MES repair cost posting to general ledger')
        op.create_index('ix_mes_repair_cost_posting_id', 'mes_repair_cost_posting', ['id'], unique=True); op.create_index('idx_repair_cost_posting_period', 'mes_repair_cost_posting', ['period_id', 'posted_at'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind()); tables = inspector.get_table_names()
    for name in ('mes_repair_cost_posting', 'mes_repair_part_issue'):
        if name in tables:
            op.drop_table(name)
