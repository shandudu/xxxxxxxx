from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.scheduling.enums import ConfigStatus, QualificationStatus, RosterStatus


class JobType(Base):
    __tablename__ = 'mes_job_type'
    __table_args__ = (
        sa.UniqueConstraint('job_code', 'deleted', name='uk_mes_job_type_code_deleted'),
        {'comment': 'MES workforce job types'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    job_code: Mapped[str] = mapped_column(sa.String(50))
    job_name: Mapped[str] = mapped_column(sa.String(100))
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    status: Mapped[ConfigStatus] = mapped_column(
        sa.String(20), default=ConfigStatus.ACTIVE, server_default=ConfigStatus.ACTIVE.value
    )


class SkillLevel(Base):
    __tablename__ = 'mes_skill_level'
    __table_args__ = (
        sa.UniqueConstraint('level_code', 'deleted', name='uk_mes_skill_level_code_deleted'),
        sa.UniqueConstraint('rank_order', 'deleted', name='uk_mes_skill_level_rank_deleted'),
        {'comment': 'MES workforce skill levels'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    level_code: Mapped[str] = mapped_column(sa.String(50))
    level_name: Mapped[str] = mapped_column(sa.String(100))
    rank_order: Mapped[int] = mapped_column(sa.Integer)
    description: Mapped[str | None] = mapped_column(UniversalText, default=None)
    status: Mapped[ConfigStatus] = mapped_column(
        sa.String(20), default=ConfigStatus.ACTIVE, server_default=ConfigStatus.ACTIVE.value
    )


class WorkerSkill(Base):
    __tablename__ = 'mes_worker_skill'
    __table_args__ = (
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_skill_user'),
        sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_skill_job'),
        sa.ForeignKeyConstraint(['skill_level_id'], ['mes_skill_level.id'], name='fk_worker_skill_level'),
        sa.UniqueConstraint('user_id', 'job_type_id', 'deleted', name='uk_mes_worker_skill_job_deleted'),
        sa.Index('idx_mes_worker_skill_user_status', 'user_id', 'status'),
        {'comment': 'MES operator job skills'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    job_type_id: Mapped[int] = mapped_column(sa.BigInteger)
    skill_level_id: Mapped[int] = mapped_column(sa.BigInteger)
    assessed_on: Mapped[date] = mapped_column(sa.Date())
    expires_on: Mapped[date | None] = mapped_column(sa.Date(), default=None)
    assessor: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    status: Mapped[QualificationStatus] = mapped_column(
        sa.String(20), default=QualificationStatus.ACTIVE, server_default=QualificationStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class WorkerCertificate(Base):
    __tablename__ = 'mes_worker_certificate'
    __table_args__ = (
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_certificate_user'),
        sa.UniqueConstraint('certificate_no', 'deleted', name='uk_mes_worker_certificate_no_deleted'),
        sa.Index('idx_mes_worker_certificate_user_type', 'user_id', 'certificate_type', 'status'),
        sa.Index('idx_mes_worker_certificate_expiry', 'expires_on', 'status'),
        {'comment': 'MES operator certificates'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    certificate_type: Mapped[str] = mapped_column(sa.String(80))
    certificate_name: Mapped[str] = mapped_column(sa.String(150))
    certificate_no: Mapped[str] = mapped_column(sa.String(100))
    issued_on: Mapped[date] = mapped_column(sa.Date())
    valid_from: Mapped[date] = mapped_column(sa.Date())
    expires_on: Mapped[date] = mapped_column(sa.Date())
    issuer: Mapped[str | None] = mapped_column(sa.String(150), default=None)
    evidence_url: Mapped[str | None] = mapped_column(sa.String(500), default=None)
    status: Mapped[QualificationStatus] = mapped_column(
        sa.String(20), default=QualificationStatus.ACTIVE, server_default=QualificationStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PositionQualificationRule(Base):
    __tablename__ = 'mes_position_qualification_rule'
    __table_args__ = (
        sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_position_rule_job'),
        sa.ForeignKeyConstraint(['minimum_skill_level_id'], ['mes_skill_level.id'], name='fk_position_rule_level'),
        sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_position_rule_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_position_rule_center'),
        sa.UniqueConstraint('rule_code', 'deleted', name='uk_mes_position_rule_code_deleted'),
        sa.Index('idx_mes_position_rule_scope', 'operation_id', 'work_center_id', 'status'),
        {'comment': 'MES operation and work-center qualification rules'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    rule_code: Mapped[str] = mapped_column(sa.String(80))
    rule_name: Mapped[str] = mapped_column(sa.String(150))
    job_type_id: Mapped[int] = mapped_column(sa.BigInteger)
    minimum_skill_level_id: Mapped[int] = mapped_column(sa.BigInteger)
    operation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    required_certificate_type: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    require_authorization: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    require_roster: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    status: Mapped[ConfigStatus] = mapped_column(
        sa.String(20), default=ConfigStatus.ACTIVE, server_default=ConfigStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class WorkerAuthorization(Base):
    __tablename__ = 'mes_worker_authorization'
    __table_args__ = (
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_authorization_user'),
        sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_authorization_job'),
        sa.ForeignKeyConstraint(['operation_id'], ['mes_operation.id'], name='fk_worker_authorization_operation'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_worker_authorization_center'),
        sa.Index('idx_mes_worker_auth_scope', 'user_id', 'work_center_id', 'operation_id', 'status'),
        {'comment': 'MES effective-dated operator position authorizations'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    job_type_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    effective_from: Mapped[date] = mapped_column(sa.Date())
    operation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    effective_to: Mapped[date | None] = mapped_column(sa.Date(), default=None)
    approved_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[QualificationStatus] = mapped_column(
        sa.String(20), default=QualificationStatus.ACTIVE, server_default=QualificationStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class WorkerRoster(Base):
    __tablename__ = 'mes_worker_roster'
    __table_args__ = (
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_worker_roster_user'),
        sa.ForeignKeyConstraint(['shift_id'], ['mes_aps_shift.id'], name='fk_worker_roster_shift'),
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_worker_roster_center'),
        sa.ForeignKeyConstraint(['job_type_id'], ['mes_job_type.id'], name='fk_worker_roster_job'),
        sa.UniqueConstraint('user_id', 'work_date', 'shift_id', 'deleted', name='uk_mes_worker_roster_shift_deleted'),
        sa.Index('idx_mes_worker_roster_date_center', 'work_date', 'work_center_id', 'status'),
        {'comment': 'MES operator shift roster'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_date: Mapped[date] = mapped_column(sa.Date())
    shift_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    job_type_id: Mapped[int] = mapped_column(sa.BigInteger)
    status: Mapped[RosterStatus] = mapped_column(
        sa.String(20), default=RosterStatus.PLANNED, server_default=RosterStatus.PLANNED.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
