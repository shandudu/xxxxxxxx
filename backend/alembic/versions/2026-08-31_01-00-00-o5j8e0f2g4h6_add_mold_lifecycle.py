"""Add mold lifecycle, cavity quality, maintenance, and cost tracking."""
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 'o5j8e0f2g4h6'
down_revision: str | None = 'n4i7d9e1f3g5'
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
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'mes_mold_asset' not in tables:
        op.create_table(
            'mes_mold_asset',
            sa.Column('mold_code', sa.String(100), nullable=False),
            sa.Column('mold_name', sa.String(200), nullable=False),
            sa.Column('tool_equipment_id', sa.BigInteger(), nullable=False),
            sa.Column('product_material_id', sa.BigInteger(), nullable=False),
            sa.Column('mold_type', sa.String(50), nullable=False),
            sa.Column('cavity_count', sa.Integer(), nullable=False),
            sa.Column('designed_life_shots', sa.BigInteger(), nullable=False),
            sa.Column('maintenance_interval_shots', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(20), server_default='AVAILABLE', nullable=False),
            sa.Column('warning_percent', sa.Numeric(5, 2), server_default='90', nullable=False),
            sa.Column('current_shots', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('shots_since_maintenance', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('mounted_equipment_id', sa.BigInteger(), nullable=True),
            sa.Column('acquisition_cost', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('residual_value', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('commission_date', sa.Date(), nullable=True),
            sa.Column('last_maintenance_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_maintenance_shots', sa.BigInteger(), nullable=True),
            sa.Column('location', sa.String(200), nullable=True),
            sa.Column('manufacturer', sa.String(150), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['tool_equipment_id'], ['mes_equipment.id'], name='fk_mold_tool_equipment'),
            sa.ForeignKeyConstraint(['product_material_id'], ['mes_material.id'], name='fk_mold_product_material'),
            sa.ForeignKeyConstraint(['mounted_equipment_id'], ['mes_equipment.id'], name='fk_mold_mounted_equipment'),
            sa.UniqueConstraint('mold_code', 'deleted', name='uk_mes_mold_code'),
            sa.UniqueConstraint('tool_equipment_id', 'deleted', name='uk_mes_mold_tool_equipment'),
            comment='MES mold lifecycle master',
        )
        op.create_index('idx_mes_mold_status', 'mes_mold_asset', ['status'])
        op.create_index('idx_mes_mold_product', 'mes_mold_asset', ['product_material_id'])
        op.create_index('idx_mes_mold_life', 'mes_mold_asset', ['current_shots', 'designed_life_shots'])
    if 'mes_mold_cavity' not in tables:
        op.create_table(
            'mes_mold_cavity',
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('cavity_no', sa.String(40), nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('current_shots', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('inspected_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('defect_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('last_defect_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_defect_code', sa.String(100), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_cavity_mold'),
            sa.UniqueConstraint('mold_id', 'cavity_no', 'deleted', name='uk_mold_cavity_no'),
            comment='MES mold cavity quality state',
        )
        op.create_index('idx_mold_cavity_status', 'mes_mold_cavity', ['mold_id', 'status'])
    if 'mes_mold_mount_record' not in tables:
        op.create_table(
            'mes_mold_mount_record',
            sa.Column('mount_no', sa.String(100), nullable=False),
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('equipment_id', sa.BigInteger(), nullable=False),
            sa.Column('mounted_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('opening_shots', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(20), server_default='MOUNTED', nullable=False),
            sa.Column('work_order_id', sa.BigInteger(), nullable=True),
            sa.Column('mounted_by', sa.BigInteger(), nullable=True),
            sa.Column('unmounted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('unmounted_by', sa.BigInteger(), nullable=True),
            sa.Column('closing_shots', sa.BigInteger(), nullable=True),
            sa.Column('produced_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('good_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('scrap_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_mount_mold'),
            sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_mold_mount_equipment'),
            sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_mount_work_order'),
            sa.UniqueConstraint('mount_no', 'deleted', name='uk_mold_mount_no'),
            comment='MES mold mounting history',
        )
        op.create_index('idx_mold_mount_active', 'mes_mold_mount_record', ['mold_id', 'status'])
        op.create_index('idx_mold_mount_work_order', 'mes_mold_mount_record', ['work_order_id', 'status'])
    if 'mes_mold_usage_record' not in tables:
        op.create_table(
            'mes_mold_usage_record',
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('mount_id', sa.BigInteger(), nullable=False),
            sa.Column('work_order_id', sa.BigInteger(), nullable=False),
            sa.Column('production_report_id', sa.BigInteger(), nullable=False),
            sa.Column('shot_count', sa.BigInteger(), nullable=False),
            sa.Column('active_cavity_count', sa.Integer(), nullable=False),
            sa.Column('good_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('scrap_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_usage_mold'),
            sa.ForeignKeyConstraint(['mount_id'], ['mes_mold_mount_record.id'], name='fk_mold_usage_mount'),
            sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_usage_work_order'),
            sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_mold_usage_report'),
            sa.UniqueConstraint('production_report_id', 'deleted', name='uk_mold_usage_report'),
            comment='MES mold shot usage from production reporting',
        )
        op.create_index('idx_mold_usage_mold_time', 'mes_mold_usage_record', ['mold_id', 'reported_at'])
    if 'mes_mold_maintenance_order' not in tables:
        op.create_table(
            'mes_mold_maintenance_order',
            sa.Column('order_no', sa.String(100), nullable=False),
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('maintenance_type', sa.String(20), nullable=False),
            sa.Column('trigger_type', sa.String(20), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('status', sa.String(20), server_default='PLANNED', nullable=False),
            sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('due_shots', sa.BigInteger(), nullable=True),
            sa.Column('repair_order_id', sa.BigInteger(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('findings', sa.Text(), nullable=True),
            sa.Column('action_taken', sa.Text(), nullable=True),
            sa.Column('labor_cost', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('material_cost', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('external_cost', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('total_cost', sa.Numeric(18, 4), server_default='0', nullable=False),
            sa.Column('assigned_user_id', sa.BigInteger(), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_maintenance_mold'),
            sa.ForeignKeyConstraint(['repair_order_id'], ['mes_repair_order.id'], name='fk_mold_maintenance_repair'),
            sa.UniqueConstraint('order_no', 'deleted', name='uk_mold_maintenance_no'),
            comment='MES mold maintenance and repair orders',
        )
        op.create_index('idx_mold_maintenance_status_due', 'mes_mold_maintenance_order', ['status', 'due_at'])
        op.create_index('idx_mold_maintenance_mold', 'mes_mold_maintenance_order', ['mold_id', 'status'])
    if 'mes_mold_cavity_quality_record' not in tables:
        op.create_table(
            'mes_mold_cavity_quality_record',
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('cavity_id', sa.BigInteger(), nullable=False),
            sa.Column('inspected_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('defect_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('result', sa.String(20), nullable=False),
            sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('work_order_id', sa.BigInteger(), nullable=True),
            sa.Column('production_report_id', sa.BigInteger(), nullable=True),
            sa.Column('inspection_id', sa.BigInteger(), nullable=True),
            sa.Column('defect_code', sa.String(100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_quality_mold'),
            sa.ForeignKeyConstraint(['cavity_id'], ['mes_mold_cavity.id'], name='fk_mold_quality_cavity'),
            sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_mold_quality_work_order'),
            sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_mold_quality_report'),
            sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_mold_quality_inspection'),
            comment='MES mold cavity quality records',
        )
        op.create_index('idx_mold_quality_cavity_time', 'mes_mold_cavity_quality_record', ['cavity_id', 'checked_at'])
        op.create_index('idx_mold_quality_result', 'mes_mold_cavity_quality_record', ['result'])
    if 'mes_mold_cost_ledger' not in tables:
        op.create_table(
            'mes_mold_cost_ledger',
            sa.Column('entry_no', sa.String(100), nullable=False),
            sa.Column('mold_id', sa.BigInteger(), nullable=False),
            sa.Column('cost_type', sa.String(20), nullable=False),
            sa.Column('amount', sa.Numeric(18, 4), nullable=False),
            sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source_type', sa.String(40), nullable=True),
            sa.Column('source_id', sa.BigInteger(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['mold_id'], ['mes_mold_asset.id'], name='fk_mold_cost_mold'),
            sa.UniqueConstraint('entry_no', 'deleted', name='uk_mold_cost_no'),
            comment='MES mold lifecycle cost ledger',
        )
        op.create_index('idx_mold_cost_mold_time', 'mes_mold_cost_ledger', ['mold_id', 'occurred_at'])
    _install_menu()


def _install_menu() -> None:
    bind = op.get_bind()
    menu = sa.table(
        'sys_menu', sa.column('id', sa.BigInteger), sa.column('title', sa.String),
        sa.column('name', sa.String), sa.column('path', sa.String), sa.column('sort', sa.Integer),
        sa.column('icon', sa.String), sa.column('type', sa.Integer), sa.column('component', sa.String),
        sa.column('perms', sa.String), sa.column('status', sa.Integer), sa.column('display', sa.Integer),
        sa.column('cache', sa.Integer), sa.column('link', sa.String), sa.column('remark', sa.String),
        sa.column('parent_id', sa.BigInteger), sa.column('created_time', sa.DateTime), sa.column('updated_time', sa.DateTime),
    )
    parent_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'System'))
    if parent_id is None:
        return
    route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesMoldLifecycle'))
    now = datetime.now()
    if route_id is None:
        bind.execute(menu.insert().values(
            title='模具全生命周期', name='MesMoldLifecycle', path='/mes/equipment/molds', sort=24,
            icon='mdi:tools', type=1, component='/plugins/equipment/views/molds',
            perms='mes:equipment:mold:view', status=1, display=1, cache=1, link='', remark=None,
            parent_id=parent_id, created_time=now, updated_time=None,
        ))
        route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesMoldLifecycle'))
    for name, title, permission in (
        ('MesMoldConfig', '模具台账配置', 'mes:equipment:mold:config'),
        ('MesMoldMount', '模具上下模', 'mes:equipment:mold:mount'),
        ('MesMoldMaintenance', '模具保养维修', 'mes:equipment:mold:maintenance'),
        ('MesMoldQuality', '模具穴位质量', 'mes:equipment:mold:quality'),
    ):
        if bind.scalar(sa.select(menu.c.id).where(menu.c.name == name)) is None:
            bind.execute(menu.insert().values(
                title=title, name=name, path=None, sort=0, icon=None, type=2, component=None,
                perms=permission, status=1, display=0, cache=1, link='', remark=None,
                parent_id=route_id, created_time=now, updated_time=None,
            ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name IN ('MesMoldConfig','MesMoldMount','MesMoldMaintenance','MesMoldQuality')"))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name = 'MesMoldLifecycle'"))
    tables = set(sa.inspect(bind).get_table_names())
    for name in (
        'mes_mold_cost_ledger', 'mes_mold_cavity_quality_record', 'mes_mold_maintenance_order',
        'mes_mold_usage_record', 'mes_mold_mount_record', 'mes_mold_cavity', 'mes_mold_asset',
    ):
        if name in tables:
            op.drop_table(name)
