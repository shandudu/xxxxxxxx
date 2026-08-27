from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.scheduling.enums import ShopfloorStatus, TeamMemberRole, WorkstationSessionStatus


class ProductionTeam(Base):
    __tablename__ = 'mes_production_team'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_production_team_center'),
        sa.ForeignKeyConstraint(['leader_user_id'], ['sys_user.id'], name='fk_production_team_leader'),
        sa.UniqueConstraint('team_code', 'deleted', name='uk_mes_production_team_code_deleted'),
        sa.Index('idx_mes_production_team_center', 'work_center_id'),
        sa.Index('idx_mes_production_team_status', 'status'),
        {'comment': 'MES production teams'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    team_code: Mapped[str] = mapped_column(sa.String(80))
    team_name: Mapped[str] = mapped_column(sa.String(150))
    work_center_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    leader_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[ShopfloorStatus] = mapped_column(
        sa.String(20), default=ShopfloorStatus.ACTIVE, server_default=ShopfloorStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class ProductionTeamMember(Base):
    __tablename__ = 'mes_production_team_member'
    __table_args__ = (
        sa.ForeignKeyConstraint(['team_id'], ['mes_production_team.id'], name='fk_team_member_team'),
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_team_member_user'),
        sa.UniqueConstraint('team_id', 'user_id', 'deleted', name='uk_mes_team_member_user_deleted'),
        sa.Index('idx_mes_team_member_user_status', 'user_id', 'status'),
        {'comment': 'MES production team members'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    team_id: Mapped[int] = mapped_column(sa.BigInteger)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    member_role: Mapped[TeamMemberRole] = mapped_column(
        sa.String(20), default=TeamMemberRole.OPERATOR, server_default=TeamMemberRole.OPERATOR.value
    )
    status: Mapped[ShopfloorStatus] = mapped_column(
        sa.String(20), default=ShopfloorStatus.ACTIVE, server_default=ShopfloorStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class Workstation(Base):
    __tablename__ = 'mes_workstation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_center_id'], ['mes_work_center.id'], name='fk_workstation_center'),
        sa.ForeignKeyConstraint(['equipment_id'], ['mes_equipment.id'], name='fk_workstation_equipment'),
        sa.UniqueConstraint('workstation_code', 'deleted', name='uk_mes_workstation_code_deleted'),
        sa.Index('idx_mes_workstation_center_status', 'work_center_id', 'status'),
        {'comment': 'MES shop-floor workstations'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    workstation_code: Mapped[str] = mapped_column(sa.String(80))
    workstation_name: Mapped[str] = mapped_column(sa.String(150))
    work_center_id: Mapped[int] = mapped_column(sa.BigInteger)
    equipment_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    terminal_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    status: Mapped[ShopfloorStatus] = mapped_column(
        sa.String(20), default=ShopfloorStatus.ACTIVE, server_default=ShopfloorStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class WorkstationSession(Base):
    __tablename__ = 'mes_workstation_session'
    __table_args__ = (
        sa.ForeignKeyConstraint(['workstation_id'], ['mes_workstation.id'], name='fk_workstation_session_station'),
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], name='fk_workstation_session_user'),
        sa.ForeignKeyConstraint(['team_id'], ['mes_production_team.id'], name='fk_workstation_session_team'),
        sa.Index('idx_workstation_session_user_status', 'user_id', 'status'),
        sa.Index('idx_workstation_session_station_status', 'workstation_id', 'status'),
        {'comment': 'MES operator workstation sessions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    workstation_id: Mapped[int] = mapped_column(sa.BigInteger)
    user_id: Mapped[int] = mapped_column(sa.BigInteger)
    signed_in_at: Mapped[datetime] = mapped_column(TimeZone)
    last_activity_at: Mapped[datetime] = mapped_column(TimeZone)
    team_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[WorkstationSessionStatus] = mapped_column(
        sa.String(20), default=WorkstationSessionStatus.ACTIVE,
        server_default=WorkstationSessionStatus.ACTIVE.value,
    )
    signed_out_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
