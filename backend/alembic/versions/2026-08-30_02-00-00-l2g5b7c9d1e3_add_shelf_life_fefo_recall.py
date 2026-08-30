"""Add lot shelf-life, FEFO isolation and recall workflow."""
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 'l2g5b7c9d1e3'
down_revision: str | None = 'k1f4a6b8c0d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def base_columns() -> list[sa.Column]:
    return [
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('deleted_time', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'mes_shelf_life_policy' not in tables:
        op.create_table(
            'mes_shelf_life_policy',
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('warning_days', sa.Integer(), server_default='30', nullable=False),
            sa.Column('critical_days', sa.Integer(), server_default='7', nullable=False),
            sa.Column('min_remaining_days_at_issue', sa.Integer(), server_default='0', nullable=False),
            sa.Column('fefo_enabled', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('auto_hold_expired', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('retest_required', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_shelf_life_policy_material'),
            sa.UniqueConstraint('material_id', 'deleted', name='uk_shelf_life_policy_material'),
            comment='Material shelf-life warning and FEFO policy',
        )
        op.create_index('idx_shelf_life_policy_status', 'mes_shelf_life_policy', ['status'])
    if 'mes_lot_expiry_alert' not in tables:
        op.create_table(
            'mes_lot_expiry_alert',
            sa.Column('policy_id', sa.BigInteger(), nullable=False),
            sa.Column('lot_id', sa.BigInteger(), nullable=False),
            sa.Column('level', sa.String(20), nullable=False),
            sa.Column('days_remaining', sa.Integer(), nullable=False),
            sa.Column('available_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('status', sa.String(20), server_default='OPEN', nullable=False),
            sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_by', sa.BigInteger(), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['policy_id'], ['mes_shelf_life_policy.id'], name='fk_expiry_alert_policy'),
            sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_expiry_alert_lot'),
            sa.UniqueConstraint('lot_id', 'deleted', name='uk_expiry_alert_lot'),
            comment='Material lot shelf-life warning',
        )
        op.create_index('idx_expiry_alert_status_level', 'mes_lot_expiry_alert', ['status', 'level'])
    if 'mes_lot_quality_hold' not in tables:
        op.create_table(
            'mes_lot_quality_hold',
            sa.Column('hold_no', sa.String(100), nullable=False),
            sa.Column('lot_id', sa.BigInteger(), nullable=False),
            sa.Column('reason', sa.String(30), nullable=False),
            sa.Column('held_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(30), server_default='OPEN', nullable=False),
            sa.Column('source_type', sa.String(40), nullable=True),
            sa.Column('source_id', sa.BigInteger(), nullable=True),
            sa.Column('source_no', sa.String(100), nullable=True),
            sa.Column('inspection_id', sa.BigInteger(), nullable=True),
            sa.Column('original_expiry_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('previous_lot_status', sa.String(30), nullable=True),
            sa.Column('previous_quality_status', sa.String(30), nullable=True),
            sa.Column('new_expiry_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_by', sa.BigInteger(), nullable=True),
            sa.Column('decision_reason', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_lot_quality_hold_lot'),
            sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_lot_quality_hold_inspection'),
            sa.UniqueConstraint('hold_no', 'deleted', name='uk_lot_quality_hold_no'),
            comment='Lot quality isolation and disposition',
        )
        op.create_index('idx_lot_quality_hold_lot_status', 'mes_lot_quality_hold', ['lot_id', 'status'])
    if 'mes_lot_recall' not in tables:
        op.create_table(
            'mes_lot_recall',
            sa.Column('recall_no', sa.String(100), nullable=False),
            sa.Column('root_lot_id', sa.BigInteger(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('severity', sa.String(20), server_default='MAJOR', nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('initiated_by', sa.BigInteger(), nullable=True),
            sa.Column('closed_by', sa.BigInteger(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['root_lot_id'], ['mes_material_lot.id'], name='fk_lot_recall_root_lot'),
            sa.UniqueConstraint('recall_no', 'deleted', name='uk_lot_recall_no'),
            comment='Lot recall case',
        )
        op.create_index('idx_lot_recall_status', 'mes_lot_recall', ['status'])
    if 'mes_lot_recall_item' not in tables:
        op.create_table(
            'mes_lot_recall_item',
            sa.Column('recall_id', sa.BigInteger(), nullable=False),
            sa.Column('item_key', sa.String(160), nullable=False),
            sa.Column('item_type', sa.String(30), nullable=False),
            sa.Column('status', sa.String(30), nullable=False),
            sa.Column('quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('lot_id', sa.BigInteger(), nullable=True),
            sa.Column('shipment_id', sa.BigInteger(), nullable=True),
            sa.Column('shipment_line_id', sa.BigInteger(), nullable=True),
            sa.Column('customer_id', sa.BigInteger(), nullable=True),
            sa.Column('action_notes', sa.Text(), nullable=True),
            sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('handled_by', sa.BigInteger(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['recall_id'], ['mes_lot_recall.id'], name='fk_lot_recall_item_recall'),
            sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_lot_recall_item_lot'),
            sa.ForeignKeyConstraint(['shipment_id'], ['erp_shipment.id'], name='fk_lot_recall_item_shipment'),
            sa.ForeignKeyConstraint(['shipment_line_id'], ['erp_shipment_line.id'], name='fk_lot_recall_item_shipment_line'),
            sa.ForeignKeyConstraint(['customer_id'], ['erp_customer.id'], name='fk_lot_recall_item_customer'),
            sa.UniqueConstraint('recall_id', 'item_key', 'deleted', name='uk_lot_recall_item_key'),
            comment='Affected inventory and customer shipment in a lot recall',
        )
        op.create_index('idx_lot_recall_item_status', 'mes_lot_recall_item', ['recall_id', 'status'])
    _install_menu()


def _install_menu() -> None:
    bind = op.get_bind()
    menu_table = sa.table(
        'sys_menu',
        sa.column('id', sa.BigInteger),
        sa.column('title', sa.String),
        sa.column('name', sa.String),
        sa.column('path', sa.String),
        sa.column('sort', sa.Integer),
        sa.column('icon', sa.String),
        sa.column('type', sa.Integer),
        sa.column('component', sa.String),
        sa.column('perms', sa.String),
        sa.column('status', sa.Integer),
        sa.column('display', sa.Integer),
        sa.column('cache', sa.Integer),
        sa.column('link', sa.String),
        sa.column('remark', sa.String),
        sa.column('parent_id', sa.BigInteger),
        sa.column('created_time', sa.DateTime),
        sa.column('updated_time', sa.DateTime),
    )
    parent_id = bind.scalar(sa.select(menu_table.c.id).where(menu_table.c.name == 'MesInventory'))
    if parent_id is None:
        return
    route_id = bind.scalar(sa.select(menu_table.c.id).where(menu_table.c.name == 'MesInventoryShelfLife'))
    now = datetime.now()
    if route_id is None:
        bind.execute(menu_table.insert().values(
            title='批次效期与召回', name='MesInventoryShelfLife', path='/mes/inventory/shelf-life',
            sort=20, icon='mdi:calendar-alert', type=1, component='/plugins/inventory/views/shelf-life',
            perms='mes:inventory:shelf-life:view', status=1, display=1, cache=1, link='', remark=None,
            parent_id=parent_id, created_time=now, updated_time=None,
        ))
        route_id = bind.scalar(sa.select(menu_table.c.id).where(menu_table.c.name == 'MesInventoryShelfLife'))
    permissions = (
        ('MesInventoryShelfLifeConfig', '效期策略配置', 'mes:inventory:shelf-life:config'),
        ('MesInventoryShelfLifeExecute', '效期隔离处置', 'mes:inventory:shelf-life:execute'),
        ('MesInventoryRecall', '批次召回处置', 'mes:inventory:recall'),
    )
    for name, title, permission in permissions:
        exists = bind.scalar(sa.select(menu_table.c.id).where(menu_table.c.name == name))
        if exists is None:
            bind.execute(menu_table.insert().values(
                title=title, name=name, path=None, sort=0, icon=None, type=2, component=None,
                perms=permission, status=1, display=0, cache=1, link='', remark=None,
                parent_id=route_id, created_time=now, updated_time=None,
            ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name IN ('MesInventoryShelfLifeConfig','MesInventoryShelfLifeExecute','MesInventoryRecall')"))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name = 'MesInventoryShelfLife'"))
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for name in (
        'mes_lot_recall_item',
        'mes_lot_recall',
        'mes_lot_quality_hold',
        'mes_lot_expiry_alert',
        'mes_shelf_life_policy',
    ):
        if name in tables:
            op.drop_table(name)
