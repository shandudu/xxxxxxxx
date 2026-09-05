"""Add configurable Chinese and English dictionary values."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'q7l0g2h4i6j8'
down_revision: str | None = 'p6k9f1g3h5i7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ZH_LABELS = {
    ('sys_status', '0'): '停用', ('sys_status', '1'): '正常',
    ('sys_choose', 'false'): '关闭', ('sys_choose', 'true'): '开启',
    ('sys_menu_type', '0'): '目录', ('sys_menu_type', '1'): '菜单',
    ('sys_menu_type', '2'): '按钮', ('sys_menu_type', '3'): '内嵌', ('sys_menu_type', '4'): '外链',
    ('sys_login_status', '0'): '失败', ('sys_login_status', '1'): '成功',
    ('sys_data_rule_operator', '0'): 'AND', ('sys_data_rule_operator', '1'): 'OR',
    ('sys_data_rule_expression', '0'): '等于(==)', ('sys_data_rule_expression', '1'): '不等于(!=)',
    ('sys_data_rule_expression', '2'): '大于(>)', ('sys_data_rule_expression', '3'): '大于等于(>=)',
    ('sys_data_rule_expression', '4'): '小于(<)', ('sys_data_rule_expression', '5'): '小于等于(<=)',
    ('sys_data_rule_expression', '6'): '包含(in)', ('sys_data_rule_expression', '7'): '不包含(not in)',
    ('sys_frontend_config', '0'): '否', ('sys_frontend_config', '1'): '是',
    ('task_strategy_type', '0'): 'Interval（间隔）', ('task_strategy_type', '1'): 'Crontab（计划）',
    ('task_period_type', 'days'): '天', ('task_period_type', 'hours'): '小时',
    ('task_period_type', 'minutes'): '分钟', ('task_period_type', 'seconds'): '秒',
    ('task_period_type', 'microseconds'): '微妙',
    ('notice', '0'): '通知', ('notice', '1'): '公告',
    ('user_online_status', '0'): '离线', ('user_online_status', '1'): '在线',
    ('sys_plugin_type', '0'): '压缩包', ('sys_plugin_type', '1'): 'GIT',
}

DEFAULT_EN_LABELS = {
    ('sys_status', '0'): 'Disabled', ('sys_status', '1'): 'Enabled',
    ('sys_choose', 'false'): 'Off', ('sys_choose', 'true'): 'On',
    ('sys_menu_type', '0'): 'Directory', ('sys_menu_type', '1'): 'Menu',
    ('sys_menu_type', '2'): 'Button', ('sys_menu_type', '3'): 'Embedded', ('sys_menu_type', '4'): 'External link',
    ('sys_login_status', '0'): 'Failed', ('sys_login_status', '1'): 'Successful',
    ('sys_data_rule_operator', '0'): 'AND', ('sys_data_rule_operator', '1'): 'OR',
    ('sys_data_rule_expression', '0'): 'Equal (==)', ('sys_data_rule_expression', '1'): 'Not equal (!=)',
    ('sys_data_rule_expression', '2'): 'Greater than (>)', ('sys_data_rule_expression', '3'): 'Greater than or equal (>=)',
    ('sys_data_rule_expression', '4'): 'Less than (<)', ('sys_data_rule_expression', '5'): 'Less than or equal (<=)',
    ('sys_data_rule_expression', '6'): 'Contains (in)', ('sys_data_rule_expression', '7'): 'Does not contain (not in)',
    ('sys_frontend_config', '0'): 'No', ('sys_frontend_config', '1'): 'Yes',
    ('task_strategy_type', '0'): 'Interval', ('task_strategy_type', '1'): 'Crontab',
    ('task_period_type', 'days'): 'Day', ('task_period_type', 'hours'): 'Hour',
    ('task_period_type', 'minutes'): 'Minute', ('task_period_type', 'seconds'): 'Second',
    ('task_period_type', 'microseconds'): 'Microsecond',
    ('notice', '0'): 'Notification', ('notice', '1'): 'Announcement',
    ('user_online_status', '0'): 'Offline', ('user_online_status', '1'): 'Online',
    ('sys_plugin_type', '0'): 'ZIP archive', ('sys_plugin_type', '1'): 'GIT',
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name']: column for column in inspector.get_columns('sys_dict_data')}
    if 'label_zh_cn' not in columns:
        op.add_column('sys_dict_data', sa.Column('label_zh_cn', sa.Text(), nullable=True, comment='简体中文值'))
    if 'label_en_us' not in columns:
        op.add_column('sys_dict_data', sa.Column('label_en_us', sa.Text(), nullable=True, comment='英文值'))
    restore_default = sa.text(
        'UPDATE sys_dict_data SET label = :label '
        'WHERE type_code = :type_code AND value = :value AND label = value AND deleted = 0'
    )
    for (type_code, value), label in DEFAULT_ZH_LABELS.items():
        bind.execute(restore_default, {'type_code': type_code, 'value': value, 'label': label})
    op.execute(sa.text('UPDATE sys_dict_data SET label_zh_cn = label WHERE label_zh_cn IS NULL'))
    seed_english = sa.text(
        'UPDATE sys_dict_data SET label_en_us = :label '
        'WHERE type_code = :type_code AND value = :value AND label_en_us IS NULL AND deleted = 0'
    )
    for (type_code, value), label in DEFAULT_EN_LABELS.items():
        bind.execute(seed_english, {'type_code': type_code, 'value': value, 'label': label})
    uniques = {item['name'] for item in sa.inspect(bind).get_unique_constraints('sys_dict_data')}
    if 'uk_sys_dict_data_type_code_label_deleted' in uniques:
        op.drop_constraint('uk_sys_dict_data_type_code_label_deleted', 'sys_dict_data', type_='unique')
    op.alter_column('sys_dict_data', 'label', existing_type=sa.String(32), type_=sa.Text(), existing_nullable=False, comment='兼容字典标签')
    op.alter_column('sys_dict_data', 'value', existing_type=sa.String(32), type_=sa.String(128), existing_nullable=False, comment='稳定字典键值')
    uniques = {item['name'] for item in sa.inspect(bind).get_unique_constraints('sys_dict_data')}
    if 'uk_sys_dict_data_type_code_value_deleted' not in uniques:
        op.create_unique_constraint('uk_sys_dict_data_type_code_value_deleted', 'sys_dict_data', ['type_code', 'value', 'deleted'])


def downgrade() -> None:
    bind = op.get_bind()
    uniques = {item['name'] for item in sa.inspect(bind).get_unique_constraints('sys_dict_data')}
    if 'uk_sys_dict_data_type_code_value_deleted' in uniques:
        op.drop_constraint('uk_sys_dict_data_type_code_value_deleted', 'sys_dict_data', type_='unique')
    op.execute(sa.text(
        'UPDATE sys_dict_data SET '
        'label = SUBSTRING(COALESCE(label_zh_cn, label), 1, 32), '
        'value = SUBSTRING(value, 1, 32)'
    ))
    op.alter_column('sys_dict_data', 'label', existing_type=sa.Text(), type_=sa.String(32), existing_nullable=False, comment='字典标签')
    op.alter_column('sys_dict_data', 'value', existing_type=sa.String(128), type_=sa.String(32), existing_nullable=False, comment='字典值')
    op.create_unique_constraint('uk_sys_dict_data_type_code_label_deleted', 'sys_dict_data', ['type_code', 'label', 'deleted'])
    columns = {column['name'] for column in sa.inspect(bind).get_columns('sys_dict_data')}
    if 'label_en_us' in columns:
        op.drop_column('sys_dict_data', 'label_en_us')
    if 'label_zh_cn' in columns:
        op.drop_column('sys_dict_data', 'label_zh_cn')
