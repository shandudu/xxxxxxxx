"""Add workforce qualifications, authorization rules, and shift rosters."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'p6k9f1g3h5i7'
down_revision: str | None = 'o5j8e0f2g4h6'
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
    if 'mes_job_type' not in tables:
        op.create_table(
            'mes_job_type',
            sa.Column('job_code', sa.String(50), nullable=False),
            sa.Column('job_name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            *base_columns(),
            sa.UniqueConstraint('job_code', 'deleted', name='uk_mes_job_type_code_deleted'),
            comment='MES workforce job types',
        )
    if 'mes_skill_level' not in tables:
        op.create_table(
            'mes_skill_level',
            sa.Column('level_code', sa.String(50), nullable=False),
            sa.Column('level_name', sa.String(100), nullable=False),
            sa.Column('rank_order', sa.Integer(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            *base_columns(),
            sa.UniqueConstraint('level_code', 'deleted', name='uk_mes_skill_level_code_deleted'),
            sa.UniqueConstraint('rank_order', 'deleted', name='uk_mes_skill_level_rank_deleted'),
            comment='MES workforce skill levels',
        )
    if 'mes_worker_skill' not in tables:
        op.create_table(
            'mes_worker_skill',
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('job_type_id', sa.BigInteger(), nullable=False),
            sa.Column('skill_level_id', sa.BigInteger(), nullable=False),
            sa.Column('assessed_on', sa.Date(), nullable=False),
            sa.Column('expires_on', sa.Date(), nullable=True),
            sa.Column('assessor', sa.String(100), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_skill_user'),
            sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_skill_job'),
            sa.ForeignKeyConstraint(['skill_level_id'], ['mes_skill_level.id'], name='fk_worker_skill_level'),
            sa.UniqueConstraint('user_id', 'job_type_id', 'deleted', name='uk_mes_worker_skill_job_deleted'),
            comment='MES operator job skills',
        )
        op.create_index('idx_mes_worker_skill_user_status', 'mes_worker_skill', ['user_id', 'status'])
    if 'mes_worker_certificate' not in tables:
        op.create_table(
            'mes_worker_certificate',
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('certificate_type', sa.String(80), nullable=False),
            sa.Column('certificate_name', sa.String(150), nullable=False),
            sa.Column('certificate_no', sa.String(100), nullable=False),
            sa.Column('issued_on', sa.Date(), nullable=False),
            sa.Column('valid_from', sa.Date(), nullable=False),
            sa.Column('expires_on', sa.Date(), nullable=False),
            sa.Column('issuer', sa.String(150), nullable=True),
            sa.Column('evidence_url', sa.String(500), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_certificate_user'),
            sa.UniqueConstraint('certificate_no', 'deleted', name='uk_mes_worker_certificate_no_deleted'),
            comment='MES operator certificates',
        )
        op.create_index('idx_mes_worker_certificate_user_type', 'mes_worker_certificate', ['user_id', 'certificate_type', 'status'])
        op.create_index('idx_mes_worker_certificate_expiry', 'mes_worker_certificate', ['expires_on', 'status'])
    if 'mes_position_qualification_rule' not in tables:
        op.create_table(
            'mes_position_qualification_rule',
            sa.Column('rule_code', sa.String(80), nullable=False),
            sa.Column('rule_name', sa.String(150), nullable=False),
            sa.Column('job_type_id', sa.BigInteger(), nullable=False),
            sa.Column('minimum_skill_level_id', sa.BigInteger(), nullable=False),
            sa.Column('operation_id', sa.BigInteger(), nullable=True),
            sa.Column('work_center_id', sa.BigInteger(), nullable=True),
            sa.Column('required_certificate_type', sa.String(80), nullable=True),
            sa.Column('require_authorization', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('require_roster', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_position_rule_job'),
            sa.ForeignKeyConstraint(['minimum_skill_level_id'], ['mes_skill_level.id'], name='fk_position_rule_level'),
            sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_position_rule_operation'),
            sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_position_rule_center'),
            sa.UniqueConstraint('rule_code', 'deleted', name='uk_mes_position_rule_code_deleted'),
            comment='MES operation and work-center qualification rules',
        )
        op.create_index('idx_mes_position_rule_scope', 'mes_position_qualification_rule', ['operation_id', 'work_center_id', 'status'])
    if 'mes_worker_authorization' not in tables:
        op.create_table(
            'mes_worker_authorization',
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('job_type_id', sa.BigInteger(), nullable=False),
            sa.Column('work_center_id', sa.BigInteger(), nullable=False),
            sa.Column('effective_from', sa.Date(), nullable=False),
            sa.Column('operation_id', sa.BigInteger(), nullable=True),
            sa.Column('effective_to', sa.Date(), nullable=True),
            sa.Column('approved_by', sa.BigInteger(), nullable=True),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_authorization_user'),
            sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_authorization_job'),
            sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_worker_authorization_operation'),
            sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_worker_authorization_center'),
            comment='MES effective-dated operator position authorizations',
        )
        op.create_index('idx_mes_worker_auth_scope', 'mes_worker_authorization', ['user_id', 'work_center_id', 'operation_id', 'status'])
    if 'mes_worker_roster' not in tables:
        op.create_table(
            'mes_worker_roster',
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('work_date', sa.Date(), nullable=False),
            sa.Column('shift_id', sa.BigInteger(), nullable=False),
            sa.Column('work_center_id', sa.BigInteger(), nullable=False),
            sa.Column('job_type_id', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(20), server_default='PLANNED', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_roster_user'),
            sa.ForeignKeyConstraint(['shift_id'], ['mes_aps_shift.id'], name='fk_worker_roster_shift'),
            sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_worker_roster_center'),
            sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_roster_job'),
            sa.UniqueConstraint('user_id', 'work_date', 'shift_id', 'deleted', name='uk_mes_worker_roster_shift_deleted'),
            comment='MES operator shift roster',
        )
        op.create_index('idx_mes_worker_roster_date_center', 'mes_worker_roster', ['work_date', 'work_center_id', 'status'])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in (
        'mes_worker_roster',
        'mes_worker_authorization',
        'mes_position_qualification_rule',
        'mes_worker_certificate',
        'mes_worker_skill',
        'mes_skill_level',
        'mes_job_type',
    ):
        if table in tables:
            op.drop_table(table)
