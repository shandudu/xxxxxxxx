"""Add supplier qualification, sample, PPAP, AVL, and periodic review lifecycle."""
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 'n4i7d9e1f3g5'
down_revision: str | None = 'm3h6c8d0e2f4'
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
    if 'erp_supplier_qualification_application' not in tables:
        op.create_table(
            'erp_supplier_qualification_application',
            sa.Column('application_no', sa.String(100), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('requested_scope', sa.Text(), nullable=False),
            sa.Column('status', sa.String(30), server_default='DRAFT', nullable=False),
            sa.Column('qualification_level', sa.String(30), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_by', sa.BigInteger(), nullable=True),
            sa.Column('decision_notes', sa.Text(), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('certificate_manifest', sa.JSON(), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_qualification_supplier'),
            sa.UniqueConstraint('application_no', 'deleted', name='uk_supplier_qualification_no'),
            comment='Supplier onboarding and qualification application',
        )
        op.create_index('idx_supplier_qualification_supplier_status', 'erp_supplier_qualification_application', ['supplier_id', 'status'])
        op.create_index('idx_supplier_qualification_review_at', 'erp_supplier_qualification_application', ['next_review_at'])
    if 'erp_supplier_qualification_audit' not in tables:
        op.create_table(
            'erp_supplier_qualification_audit',
            sa.Column('audit_no', sa.String(100), nullable=False),
            sa.Column('application_id', sa.BigInteger(), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('audit_type', sa.String(20), nullable=False),
            sa.Column('planned_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(20), server_default='PLANNED', nullable=False),
            sa.Column('conducted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('score', sa.Numeric(5, 2), nullable=True),
            sa.Column('result', sa.String(20), nullable=True),
            sa.Column('findings', sa.Text(), nullable=True),
            sa.Column('corrective_due_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('evidence_manifest', sa.JSON(), nullable=True),
            sa.Column('auditor_id', sa.BigInteger(), nullable=True),
            sa.Column('remark', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_audit_application'),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_audit_supplier'),
            sa.UniqueConstraint('audit_no', 'deleted', name='uk_supplier_audit_no'),
            comment='Supplier qualification and periodic audit',
        )
        op.create_index('idx_supplier_audit_application', 'erp_supplier_qualification_audit', ['application_id', 'status'])
        op.create_index('idx_supplier_audit_supplier_planned', 'erp_supplier_qualification_audit', ['supplier_id', 'planned_at'])
    if 'erp_supplier_sample_approval' not in tables:
        op.create_table(
            'erp_supplier_sample_approval',
            sa.Column('sample_no', sa.String(100), nullable=False),
            sa.Column('application_id', sa.BigInteger(), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('round_no', sa.Integer(), nullable=False),
            sa.Column('submitted_quantity', sa.Numeric(18, 6), nullable=False),
            sa.Column('status', sa.String(20), server_default='PENDING', nullable=False),
            sa.Column('inspection_id', sa.BigInteger(), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_by', sa.BigInteger(), nullable=True),
            sa.Column('decision_notes', sa.Text(), nullable=True),
            sa.Column('evidence_manifest', sa.JSON(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_sample_application'),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_sample_supplier'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_sample_material'),
            sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_supplier_sample_inspection'),
            sa.UniqueConstraint('sample_no', 'deleted', name='uk_supplier_sample_no'),
            comment='Supplier material sample approval rounds',
        )
        op.create_index('idx_supplier_sample_application_material', 'erp_supplier_sample_approval', ['application_id', 'material_id'])
        op.create_index('idx_supplier_sample_status', 'erp_supplier_sample_approval', ['status'])
    if 'erp_supplier_ppap_submission' not in tables:
        op.create_table(
            'erp_supplier_ppap_submission',
            sa.Column('ppap_no', sa.String(100), nullable=False),
            sa.Column('application_id', sa.BigInteger(), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('level', sa.Integer(), nullable=False),
            sa.Column('version', sa.String(40), nullable=False),
            sa.Column('status', sa.String(20), server_default='DRAFT', nullable=False),
            sa.Column('sample_approval_id', sa.BigInteger(), nullable=True),
            sa.Column('document_manifest', sa.JSON(), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('decided_by', sa.BigInteger(), nullable=True),
            sa.Column('decision_notes', sa.Text(), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['application_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_ppap_application'),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_ppap_supplier'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_ppap_material'),
            sa.ForeignKeyConstraint(['sample_approval_id'], ['erp_supplier_sample_approval.id'], name='fk_supplier_ppap_sample'),
            sa.UniqueConstraint('ppap_no', 'deleted', name='uk_supplier_ppap_no'),
            sa.UniqueConstraint('supplier_id', 'material_id', 'version', 'deleted', name='uk_supplier_ppap_version'),
            comment='Supplier PPAP and APQP approval package',
        )
        op.create_index('idx_supplier_ppap_application_status', 'erp_supplier_ppap_submission', ['application_id', 'status'])
        op.create_index('idx_supplier_ppap_expiry', 'erp_supplier_ppap_submission', ['expires_at'])
    if 'erp_supplier_approved_material' not in tables:
        op.create_table(
            'erp_supplier_approved_material',
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('material_id', sa.BigInteger(), nullable=False),
            sa.Column('supplier_material_id', sa.BigInteger(), nullable=False),
            sa.Column('qualification_id', sa.BigInteger(), nullable=False),
            sa.Column('ppap_id', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(20), server_default='APPROVED', nullable=False),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_review_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('restrictions', sa.Text(), nullable=True),
            sa.Column('approved_by', sa.BigInteger(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_avl_supplier'),
            sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_supplier_avl_material'),
            sa.ForeignKeyConstraint(['supplier_material_id'], ['erp_supplier_material.id'], name='fk_supplier_avl_relation'),
            sa.ForeignKeyConstraint(['qualification_id'], ['erp_supplier_qualification_application.id'], name='fk_supplier_avl_qualification'),
            sa.ForeignKeyConstraint(['ppap_id'], ['erp_supplier_ppap_submission.id'], name='fk_supplier_avl_ppap'),
            sa.UniqueConstraint('supplier_id', 'material_id', 'deleted', name='uk_supplier_avl_supplier_material'),
            comment='Approved vendor list by supplier and material',
        )
        op.create_index('idx_supplier_avl_material_status', 'erp_supplier_approved_material', ['material_id', 'status'])
        op.create_index('idx_supplier_avl_supplier_status', 'erp_supplier_approved_material', ['supplier_id', 'status'])
        op.create_index('idx_supplier_avl_next_review', 'erp_supplier_approved_material', ['next_review_at'])
    if 'erp_supplier_periodic_review' not in tables:
        op.create_table(
            'erp_supplier_periodic_review',
            sa.Column('review_no', sa.String(100), nullable=False),
            sa.Column('supplier_id', sa.BigInteger(), nullable=False),
            sa.Column('avl_id', sa.BigInteger(), nullable=False),
            sa.Column('planned_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(20), server_default='PLANNED', nullable=False),
            sa.Column('quality_assessment_id', sa.BigInteger(), nullable=True),
            sa.Column('score_snapshot', sa.Numeric(5, 2), nullable=True),
            sa.Column('decision', sa.String(20), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('reviewed_by', sa.BigInteger(), nullable=True),
            sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            *base_columns(),
            sa.ForeignKeyConstraint(['supplier_id'], ['erp_supplier.id'], name='fk_supplier_review_supplier'),
            sa.ForeignKeyConstraint(['avl_id'], ['erp_supplier_approved_material.id'], name='fk_supplier_review_avl'),
            sa.ForeignKeyConstraint(['quality_assessment_id'], ['mes_supplier_quality_assessment.id'], name='fk_supplier_review_assessment'),
            sa.UniqueConstraint('review_no', 'deleted', name='uk_supplier_review_no'),
            comment='Supplier AVL periodic review decision history',
        )
        op.create_index('idx_supplier_review_status_planned', 'erp_supplier_periodic_review', ['status', 'planned_at'])
        op.create_index('idx_supplier_review_supplier', 'erp_supplier_periodic_review', ['supplier_id', 'reviewed_at'])
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
    parent_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'System'))
    if parent_id is None:
        return
    route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'ErpSupplierLifecycle'))
    now = datetime.now()
    if route_id is None:
        bind.execute(menu.insert().values(
            title='供应商准入与AVL', name='ErpSupplierLifecycle', path='/erp/supplier/lifecycle', sort=22,
            icon='mdi:clipboard-check-outline', type=1, component='/plugins/supplier/views/lifecycle',
            perms='erp:supplier:lifecycle:view', status=1, display=1, cache=1, link='', remark=None,
            parent_id=parent_id, created_time=now, updated_time=None,
        ))
        route_id = bind.scalar(sa.select(menu.c.id).where(menu.c.name == 'ErpSupplierLifecycle'))
    for name, title, permission in (
        ('ErpSupplierLifecycleQualification', '供应商准入管理', 'erp:supplier:lifecycle:qualification'),
        ('ErpSupplierLifecycleAudit', '供应商审厂管理', 'erp:supplier:lifecycle:audit'),
        ('ErpSupplierLifecycleSample', '供应商样品承认', 'erp:supplier:lifecycle:sample'),
        ('ErpSupplierLifecyclePpap', '供应商PPAP管理', 'erp:supplier:lifecycle:ppap'),
        ('ErpSupplierLifecycleApprove', '供应商准入审批', 'erp:supplier:lifecycle:approve'),
        ('ErpSupplierLifecycleReview', '供应商复审淘汰', 'erp:supplier:lifecycle:review'),
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
        "DELETE FROM sys_menu WHERE name IN ("
        "'ErpSupplierLifecycleQualification','ErpSupplierLifecycleAudit','ErpSupplierLifecycleSample',"
        "'ErpSupplierLifecyclePpap','ErpSupplierLifecycleApprove','ErpSupplierLifecycleReview')"
    ))
    bind.execute(sa.text("DELETE FROM sys_menu WHERE name = 'ErpSupplierLifecycle'"))
    tables = set(sa.inspect(bind).get_table_names())
    for name in (
        'erp_supplier_periodic_review',
        'erp_supplier_approved_material',
        'erp_supplier_ppap_submission',
        'erp_supplier_sample_approval',
        'erp_supplier_qualification_audit',
        'erp_supplier_qualification_application',
    ):
        if name in tables:
            op.drop_table(name)
