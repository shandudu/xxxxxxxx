"""Add supplier quality management, SCAR and procurement scoring."""
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 'm3h6c8d0e2f4'
down_revision: str | None = 'l2g5b7c9d1e3'
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
    if 'mes_supplier_quality_policy' not in tables:
        op.create_table(
            'mes_supplier_quality_policy',
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('rolling_days', sa.Integer(), server_default='180', nullable=False),
            sa.Column('minimum_inspections', sa.Integer(), server_default='1', nullable=False),
            sa.Column('excellent_score', sa.Numeric(5, 2), server_default='95', nullable=False),
            sa.Column('qualified_score', sa.Numeric(5, 2), server_default='85', nullable=False),
            sa.Column('conditional_score', sa.Numeric(5, 2), server_default='70', nullable=False),
            sa.Column('quality_weight', sa.Numeric(5, 2), server_default='70', nullable=False),
            sa.Column('delivery_weight', sa.Numeric(5, 2), server_default='30', nullable=False),
            sa.Column('auto_apply', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('block_on_open_critical_scar', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=False),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_quality_policy_supplier'),
            sa.UniqueConstraint('supplier_id', 'deleted', name='uk_supplier_quality_policy_supplier'),
            comment='SQM scoring policy and procurement thresholds',
        )
        op.create_index('idx_supplier_quality_policy_status', 'mes_supplier_quality_policy', ['status'])
    if 'mes_supplier_corrective_action' not in tables:
        op.create_table(
            'mes_supplier_corrective_action',
            sa.Column('scar_no', sa.String(100), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('ncr_id', sa.BigInteger(), nullable=False),
            sa.Column('inspection_id', sa.BigInteger(), nullable=False),
            sa.Column('supplier_receipt_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('nonconforming_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('defect_description', sa.Text(), nullable=False),
            sa.Column('status', sa.String(30), server_default='DRAFT', nullable=False),
            sa.Column('severity', sa.String(20), server_default='MAJOR', nullable=False),
            sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('containment_action', sa.Text(), nullable=True),
            sa.Column('root_cause', sa.Text(), nullable=True),
            sa.Column('corrective_action', sa.Text(), nullable=True),
            sa.Column('preventive_action', sa.Text(), nullable=True),
            sa.Column('response_evidence', sa.Text(), nullable=True),
            sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('disposition_id', sa.BigInteger(), nullable=True),
            sa.Column('reinspection_id', sa.BigInteger(), nullable=True),
            sa.Column('verification_result', sa.String(20), nullable=True),
            sa.Column('verification_notes', sa.Text(), nullable=True),
            sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('verified_by', sa.BigInteger(), nullable=True),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_scar_supplier'),
            sa.ForeignKeyConstraint(['ncr_id'], ['mes_nonconformance_report.id'], name='fk_scar_ncr'),
            sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_scar_inspection'),
            sa.ForeignKeyConstraint(['supplier_receipt_id'], ['erp_supplier_receipt.id'], name='fk_scar_receipt'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_scar_material'),
            sa.ForeignKeyConstraint(['disposition_id'], ['mes_nonconformance_disposition.id'], name='fk_scar_disposition'),
            sa.ForeignKeyConstraint(['reinspection_id'], ['mes_quality_inspection.id'], name='fk_scar_reinspection'),
            sa.UniqueConstraint('scar_no', 'deleted', name='uk_mes_scar_no'),
            sa.UniqueConstraint('ncr_id', 'deleted', name='uk_mes_scar_ncr'),
            comment='Supplier corrective action request from incoming quality NCR',
        )
        op.create_index('idx_mes_scar_supplier_status', 'mes_supplier_corrective_action', ['supplier_id', 'status'])
        op.create_index('idx_mes_scar_due_at', 'mes_supplier_corrective_action', ['due_at'])
    if 'mes_supplier_quality_assessment' not in tables:
        op.create_table(
            'mes_supplier_quality_assessment',
            sa.Column('assessment_no', sa.String(100), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('policy_id', sa.BigInteger(), nullable=False),
            sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
            sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
            sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('grade', sa.String(20), nullable=False),
            sa.Column('procurement_decision', sa.String(30), nullable=False),
            sa.Column('overall_score', sa.Numeric(5, 2), nullable=False),
            sa.Column('inspection_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('passed_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('failed_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('inspected_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('rejected_quantity', sa.Numeric(18, 6), server_default='0', nullable=False),
            sa.Column('pass_rate', sa.Numeric(7, 2), server_default='0', nullable=False),
            sa.Column('acceptance_rate', sa.Numeric(7, 2), server_default='0', nullable=False),
            sa.Column('scar_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('scar_closed_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('scar_on_time_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('corrective_score', sa.Numeric(7, 2), server_default='0', nullable=False),
            sa.Column('quality_score', sa.Numeric(7, 2), server_default='0', nullable=False),
            sa.Column('delivery_line_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('otif_line_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('delivery_score', sa.Numeric(7, 2), server_default='0', nullable=False),
            sa.Column('critical_scar_open', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('applied_notes', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_quality_assessment_supplier'),
            sa.ForeignKeyConstraint(['policy_id'], ['mes_supplier_quality_policy.id'], name='fk_supplier_quality_assessment_policy'),
            sa.UniqueConstraint('assessment_no', 'deleted', name='uk_supplier_quality_assessment_no'),
            comment='Supplier quality, corrective action and OTIF score history',
        )
        op.create_index('idx_supplier_quality_assessment_supplier', 'mes_supplier_quality_assessment', ['supplier_id', 'assessed_at'])
        op.create_index('idx_supplier_quality_assessment_decision', 'mes_supplier_quality_assessment', ['procurement_decision'])
    _install_menu()


def _install_menu() -> None:
    bind = op.get_bind()
    menu = sa.table(
        'sys_menu',
        sa.column('id', sa.BigInteger), sa.column('title', sa.String), sa.column('name', sa.String),
        sa.column('path', sa.String), sa.column('sort', sa.Integer), sa.column('icon', sa.String),
        sa.column('type', sa.Integer), sa.column('component', sa.String), sa.column('perms', sa.String),
        sa.column('status', sa.Integer), sa.column('display', sa.Integer), sa.column('cache', sa.Integer),
        sa.column('link', sa.String), sa.column('remark', sa.String), sa.column('parent_id', sa.BigInteger),
        sa.column('created_time', sa.DateTime), sa.column('updated_time', sa.DateTime),
    )
    parent_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesQuality'))
    if parent_id is None:
        return
    route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesSupplierQuality'))
    now = datetime.now()
    if route_id is None:
        bind.execute(menu.insert().values(
            title='供应商质量管理', name='MesSupplierQuality', path='/mes/quality/sqm', sort=20,
            icon='mdi:account-hard-hat-outline', type=1, component='/plugins/quality/views/sqm',
            perms='mes:quality:sqm:view', status=1, display=1, cache=1, link='', remark=None,
            parent_id=parent_id, created_time=now, updated_time=None,
        ))
        route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'MesSupplierQuality'))
    for name, title, permission in (
        ('MesSupplierQualityScar', '供应商整改管理', 'mes:quality:sqm:scar'),
        ('MesSupplierQualityVerify', '供应商整改验证', 'mes:quality:sqm:verify'),
        ('MesSupplierQualityPolicy', '供应商质量策略', 'mes:quality:sqm:policy'),
    ):
        if bind.scalar(sa.select(menu.c.id).where(menu.c.name == name)) is None:
            bind.execute(menu.insert().values(
                title=title, name=name, path=None, sort=0, icon=None, type=2, component=None,
                perms=permission, status=1, display=0, cache=1, link='', remark=None,
                parent_id=route_id, created_time=now, updated_time=None,
            ))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM sys_menu WHERE name IN ('MesSupplierQualityScar','MesSupplierQualityVerify','MesSupplierQualityPolicy')"
    ))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name = 'MesSupplierQuality'"))
    tables = set(sa.inspect(bind).get_table_names())
    for name in (
        'mes_supplier_quality_assessment',
        'mes_supplier_corrective_action',
        'mes_supplier_quality_policy',
    ):
        if name in tables:
            op.drop_table(name)
