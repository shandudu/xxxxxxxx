"""Add finished-goods scan packaging, HU and quality release."""
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 's9n2i4j6k8l0'
down_revision: str | None = 'r8m1h3i5j7k9'
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
    if 'mes_packaging_specification' not in tables:
        op.create_table(
            'mes_packaging_specification',
            sa.Column('spec_code', sa.String(80), nullable=False),
            sa.Column('spec_name', sa.String(150), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('units_per_carton', sa.Numeric(18, 6), nullable=False),
            sa.Column('version', sa.String(30), server_default='V1', nullable=False),
            sa.Column('cartons_per_pallet', sa.Integer(), nullable=True),
            sa.Column('allow_mixed_lot', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('allow_partial_carton', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('require_quality_release', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('require_weight_check', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('target_gross_weight', sa.Numeric(18, 6), nullable=True),
            sa.Column('weight_tolerance', sa.Numeric(18, 6), nullable=True),
            sa.Column('label_template_code', sa.String(80), nullable=True),
            sa.Column('effective_from', sa.Date(), nullable=True),
            sa.Column('effective_to', sa.Date(), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_spec_material'),
            sa.UniqueConstraint('spec_code', 'version', 'deleted', name='uk_packaging_spec_code_version'),
            comment='Finished-goods packaging specifications',
        )
        op.create_index('idx_packaging_spec_material_status', 'mes_packaging_specification', ['material_id', 'status'])
    if 'mes_packaging_task' not in tables:
        op.create_table(
            'mes_packaging_task',
            sa.Column('task_no', sa.String(100), nullable=False),
            sa.Column('production_report_id', sa.BigInteger(), nullable=False),
            sa.Column('work_order_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('specification_id', sa.BigInteger(), nullable=False),
            sa.Column('planned_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('lot_id', sa.BigInteger(), nullable=True),
            sa.Column('stock_transaction_id', sa.BigInteger(), nullable=True),
            sa.Column('idempotency_key', sa.String(180), nullable=True),
            sa.Column('packed_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('status', sa.String(30), server_default='DRAFT', nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('packed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_packaging_task_report'),
            sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_packaging_task_order'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_task_material'),
            sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_packaging_task_lot'),
            sa.ForeignKeyConstraint(['specification_id'], ['mes_packaging_specification.id'], name='fk_packaging_task_spec'),
            sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_packaging_task_stock_tx'),
            sa.UniqueConstraint('task_no', 'deleted', name='uk_packaging_task_no_deleted'),
            sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_task_idempotency'),
            comment='Finished-goods packaging tasks',
        )
        op.create_index('idx_packaging_task_report', 'mes_packaging_task', ['production_report_id'])
        op.create_index('idx_packaging_task_status', 'mes_packaging_task', ['status'])
    if 'mes_packaging_handling_unit' not in tables:
        op.create_table(
            'mes_packaging_handling_unit',
            sa.Column('hu_code', sa.String(120), nullable=False),
            sa.Column('task_id', sa.BigInteger(), nullable=False),
            sa.Column('hu_type', sa.String(20), nullable=False),
            sa.Column('capacity', sa.Numeric(18, 6), nullable=False),
            sa.Column('parent_hu_id', sa.BigInteger(), nullable=True),
            sa.Column('quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('tare_weight', sa.Numeric(18, 6), nullable=True),
            sa.Column('gross_weight', sa.Numeric(18, 6), nullable=True),
            sa.Column('net_weight', sa.Numeric(18, 6), nullable=True),
            sa.Column('weight_result', sa.String(20), nullable=True),
            sa.Column('status', sa.String(30), server_default='OPEN', nullable=False),
            sa.Column('sealed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('stored_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['task_id'], ['mes_packaging_task.id'], name='fk_packaging_hu_task'),
            sa.ForeignKeyConstraint(['parent_hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_hu_parent'),
            sa.UniqueConstraint('hu_code', 'deleted', name='uk_packaging_hu_code_deleted'),
            comment='Packaging handling units (HU)',
        )
        op.create_index('idx_packaging_hu_task_status', 'mes_packaging_handling_unit', ['task_id', 'status'])
    if 'mes_packaging_hu_content' not in tables:
        op.create_table(
            'mes_packaging_hu_content',
            sa.Column('hu_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('production_report_id', sa.BigInteger(), nullable=False),
            sa.Column('scan_type', sa.String(20), nullable=False),
            sa.Column('scanned_code', sa.String(120), nullable=False),
            sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('scan_key', sa.String(180), nullable=False),
            sa.Column('lot_id', sa.BigInteger(), nullable=True),
            sa.Column('serial_id', sa.BigInteger(), nullable=True),
            sa.Column('scanned_by', sa.BigInteger(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_content_hu'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_content_material'),
            sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_packaging_content_lot'),
            sa.ForeignKeyConstraint(['serial_id'], ['mes_material_serial.id'], name='fk_packaging_content_serial'),
            sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_packaging_content_report'),
            sa.UniqueConstraint('scan_key', 'deleted', name='uk_packaging_content_scan_key'),
            comment='Lot and serial contents scanned into packaging HUs',
        )
        op.create_index('idx_packaging_content_hu', 'mes_packaging_hu_content', ['hu_id'])
        op.create_index('idx_packaging_content_serial', 'mes_packaging_hu_content', ['serial_id'])
    if 'mes_packaging_weight_record' not in tables:
        op.create_table(
            'mes_packaging_weight_record',
            sa.Column('hu_id', sa.BigInteger(), nullable=False),
            sa.Column('gross_weight', sa.Numeric(18, 6), nullable=False),
            sa.Column('tare_weight', sa.Numeric(18, 6), nullable=False),
            sa.Column('net_weight', sa.Numeric(18, 6), nullable=False),
            sa.Column('result', sa.String(20), nullable=False),
            sa.Column('idempotency_key', sa.String(180), nullable=False),
            sa.Column('measured_by', sa.BigInteger(), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_weight_hu'),
            sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_weight_idempotency'),
            comment='Packaging weight checks',
        )
    if 'mes_packaging_inspection' not in tables:
        op.create_table(
            'mes_packaging_inspection',
            sa.Column('hu_id', sa.BigInteger(), nullable=False),
            sa.Column('result', sa.String(20), nullable=False),
            sa.Column('idempotency_key', sa.String(180), nullable=False),
            sa.Column('appearance_passed', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('quantity_passed', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('label_passed', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('inspected_by', sa.BigInteger(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_inspection_hu'),
            sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_inspection_idempotency'),
            comment='Packaging inspection decisions',
        )
    if 'mes_packaging_label_print' not in tables:
        op.create_table(
            'mes_packaging_label_print',
            sa.Column('hu_id', sa.BigInteger(), nullable=False),
            sa.Column('template_code', sa.String(80), nullable=False),
            sa.Column('copies', sa.Integer(), server_default='1', nullable=False),
            sa.Column('printer_name', sa.String(120), nullable=True),
            sa.Column('idempotency_key', sa.String(180), nullable=False),
            sa.Column('printed_by', sa.BigInteger(), nullable=True),
            sa.Column('reason', sa.String(500), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_label_hu'),
            sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_label_idempotency'),
            comment='Packaging label print history',
        )
    _install_menu()
    _install_tips()


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
    route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesPackaging'))
    now = datetime.now()
    if route_id is None:
        bind.execute(menu.insert().values(
            title='packaging.menu', name='MesPackaging', path='/mes/packaging', sort=26,
            icon='mdi:package-variant-closed-check', type=1, component='/plugins/packaging/views/index',
            perms='mes:packaging:view', status=1, display=1, cache=1, link='', remark=None,
            parent_id=parent_id, created_time=now, updated_time=None,
        ))
        route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesPackaging'))
    for name, title, permission in (
        ('MesPackagingManage', '包装规格与任务管理', 'mes:packaging:manage'),
        ('MesPackagingExecute', '扫码装箱与标签打印', 'mes:packaging:execute'),
        ('MesPackagingInspect', '包装检验', 'mes:packaging:inspect'),
        ('MesPackagingRelease', '包装入库放行', 'mes:packaging:release'),
    ):
        if bind.scalar(sa.select(menu.c.id).where(menu.c.name == name)) is None:
            bind.execute(menu.insert().values(
                title=title, name=name, path=None, sort=0, icon=None, type=2, component=None,
                perms=permission, status=1, display=0, cache=1, link='', remark=None,
                parent_id=route_id, created_time=now, updated_time=None,
            ))


def _install_tips() -> None:
    bind = op.get_bind()
    type_id = bind.scalar(sa.text("SELECT id FROM sys_dict_type WHERE code='ui_tips' AND deleted=0"))
    if type_id is None:
        return
    messages = (
        ('packaging.specCreated', '包装规格已创建', 'Packaging specification created'),
        ('packaging.taskCreated', '包装任务已创建', 'Packaging task created'),
        ('packaging.taskReleased', '包装任务已下达', 'Packaging task released'),
        ('packaging.huCreated', '包装箱码已创建', 'Packaging handling unit created'),
        ('packaging.scanAccepted', '扫码装箱成功', 'Item scan accepted'),
        ('packaging.weightRecorded', '称重结果已记录', 'Weight result recorded'),
        ('packaging.huSealed', '封箱完成', 'Handling unit sealed'),
        ('packaging.inspectionCompleted', '包装检验已完成', 'Packaging inspection completed'),
        ('packaging.labelRecorded', '标签打印记录已保存', 'Label print record saved'),
        ('packaging.releasedToStock', '包装成品已放行入库', 'Packaged goods released to stock'),
    )
    statement = sa.text(
        'INSERT INTO sys_dict_data '
        '(type_code,label,value,label_zh_cn,label_en_us,color,sort,status,remark,type_id,created_time,updated_time,deleted) '
        "SELECT 'ui_tips',:zh,:value,:zh,:en,NULL,:sort,1,:remark,:type_id,CURRENT_TIMESTAMP,NULL,0 "
        "WHERE NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE type_code='ui_tips' AND value=:value AND deleted=0)"
    )
    for sort, (value, zh, en) in enumerate(messages, start=200):
        bind.execute(statement, {'value': value, 'zh': zh, 'en': en, 'sort': sort, 'type_id': type_id, 'remark': f'内置可配置消息：{value}'})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM sys_dict_data WHERE type_code='ui_tips' AND value LIKE 'packaging.%' AND remark LIKE '内置可配置消息：packaging.%'"))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name IN ('MesPackagingManage','MesPackagingExecute','MesPackagingInspect','MesPackagingRelease')"))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name='MesPackaging'"))
    tables = set(sa.inspect(bind).get_table_names())
    for table in (
        'mes_packaging_label_print', 'mes_packaging_inspection', 'mes_packaging_weight_record',
        'mes_packaging_hu_content', 'mes_packaging_handling_unit', 'mes_packaging_task',
        'mes_packaging_specification',
    ):
        if table in tables:
            op.drop_table(table)
