from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.app.admin.model.user import User
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.equipment.model import Equipment
from backend.plugin.production.schema.execution import CompleteProductionExecution, StartProductionExecution
from backend.plugin.production.service.execution_service import production_execution_service
from backend.plugin.routing.enums import WorkCenterStatus
from backend.plugin.routing.model import WorkCenter
from backend.plugin.scheduling.enums import DispatchStatus, OperationScheduleStatus, ShopfloorStatus, WorkstationSessionStatus
from backend.plugin.scheduling.model import ApsDispatch, ApsOperationSchedule, ProductionTeam, ProductionTeamMember, Workstation, WorkstationSession
from backend.plugin.scheduling.schema.shopfloor import (
    CheckInInput,
    CompleteDispatchInput,
    StatusInput,
    TeamDetail,
    TeamInput,
    TeamMemberDetail,
    TeamMemberInput,
    TerminalContext,
    TerminalDispatchDetail,
    UserOption,
    WorkstationDetail,
    WorkstationInput,
    WorkstationOption,
    WorkstationSessionDetail,
)
from backend.utils.timezone import timezone


class ShopfloorService:
    @staticmethod
    def user_id() -> int:
        try:
            user_id = ctx.user_id
        except (AttributeError, LookupError, ContextDoesNotExistError):
            raise errors.AuthorizationError(msg='OPERATOR_CONTEXT_REQUIRED') from None
        return int(user_id)

    @staticmethod
    async def users(db: AsyncSession) -> list[UserOption]:
        rows = (await db.scalars(select(User).where(User.deleted == 0, User.status == 1).order_by(User.username))).all()
        return [UserOption(id=row.id, username=row.username, nickname=row.nickname) for row in rows]

    @staticmethod
    async def _team(db: AsyncSession, team_id: int, lock: bool = False) -> ProductionTeam:
        stmt = select(ProductionTeam).where(ProductionTeam.id == team_id, ProductionTeam.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='PRODUCTION_TEAM_NOT_FOUND')
        return row

    @staticmethod
    async def _validate_team_refs(db: AsyncSession, obj: TeamInput) -> None:
        if obj.work_center_id and not await db.scalar(select(WorkCenter.id).where(WorkCenter.id == obj.work_center_id, WorkCenter.deleted == 0, WorkCenter.status == WorkCenterStatus.ACTIVE)):
            raise errors.NotFoundError(msg='WORK_CENTER_NOT_FOUND')
        if obj.leader_user_id and not await db.scalar(select(User.id).where(User.id == obj.leader_user_id, User.deleted == 0, User.status == 1)):
            raise errors.NotFoundError(msg='LEADER_USER_NOT_FOUND')

    @staticmethod
    async def _team_detail(db: AsyncSession, row: ProductionTeam) -> TeamDetail:
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == row.work_center_id, WorkCenter.deleted == 0)) if row.work_center_id else None
        leader = await db.scalar(select(User).where(User.id == row.leader_user_id, User.deleted == 0)) if row.leader_user_id else None
        members = (await db.scalars(select(ProductionTeamMember).where(ProductionTeamMember.team_id == row.id, ProductionTeamMember.deleted == 0).order_by(ProductionTeamMember.id))).all()
        users = {user.id: user for user in (await db.scalars(select(User).where(User.id.in_([item.user_id for item in members])))).all()} if members else {}
        result = TeamDetail.model_validate(row)
        result.work_center_code = center.work_center_code if center else None
        result.work_center_name = center.work_center_name if center else None
        result.leader_username = leader.username if leader else None
        result.members = [TeamMemberDetail.model_validate(item).model_copy(update={'username': users[item.user_id].username if item.user_id in users else '', 'nickname': users[item.user_id].nickname if item.user_id in users else ''}) for item in members]
        return result

    @staticmethod
    async def list_teams(db: AsyncSession) -> list[TeamDetail]:
        rows = (await db.scalars(select(ProductionTeam).where(ProductionTeam.deleted == 0).order_by(ProductionTeam.team_code))).all()
        return [await ShopfloorService._team_detail(db, row) for row in rows]

    @staticmethod
    async def create_team(db: AsyncSession, obj: TeamInput) -> TeamDetail:
        await ShopfloorService._validate_team_refs(db, obj)
        if await db.scalar(select(ProductionTeam.id).where(ProductionTeam.team_code == obj.team_code, ProductionTeam.deleted == 0)):
            raise errors.ConflictError(msg='PRODUCTION_TEAM_CODE_EXISTS')
        row = ProductionTeam(**obj.model_dump())
        row.created_by = ShopfloorService.user_id()
        db.add(row)
        await db.flush()
        return await ShopfloorService._team_detail(db, row)

    @staticmethod
    async def update_team(db: AsyncSession, team_id: int, obj: TeamInput) -> TeamDetail:
        row = await ShopfloorService._team(db, team_id, True)
        await ShopfloorService._validate_team_refs(db, obj)
        duplicate = await db.scalar(select(ProductionTeam.id).where(ProductionTeam.team_code == obj.team_code, ProductionTeam.id != row.id, ProductionTeam.deleted == 0))
        if duplicate:
            raise errors.ConflictError(msg='PRODUCTION_TEAM_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(row, key, value)
        row.updated_by = ShopfloorService.user_id()
        await db.flush()
        return await ShopfloorService._team_detail(db, row)

    @staticmethod
    async def team_status(db: AsyncSession, team_id: int, obj: StatusInput) -> TeamDetail:
        row = await ShopfloorService._team(db, team_id, True)
        row.status = obj.status
        row.updated_by = ShopfloorService.user_id()
        await db.flush()
        return await ShopfloorService._team_detail(db, row)

    @staticmethod
    async def add_member(db: AsyncSession, team_id: int, obj: TeamMemberInput) -> TeamDetail:
        team = await ShopfloorService._team(db, team_id, True)
        if team.status != ShopfloorStatus.ACTIVE:
            raise errors.ConflictError(msg='PRODUCTION_TEAM_DISABLED')
        if not await db.scalar(select(User.id).where(User.id == obj.user_id, User.deleted == 0, User.status == 1)):
            raise errors.NotFoundError(msg='TEAM_MEMBER_USER_NOT_FOUND')
        exists = await db.scalar(select(ProductionTeamMember.id).where(ProductionTeamMember.team_id == team.id, ProductionTeamMember.user_id == obj.user_id, ProductionTeamMember.deleted == 0))
        if exists:
            raise errors.ConflictError(msg='TEAM_MEMBER_EXISTS')
        row = ProductionTeamMember(team_id=team.id, user_id=obj.user_id, member_role=obj.member_role, remark=obj.remark)
        row.created_by = ShopfloorService.user_id()
        db.add(row)
        await db.flush()
        return await ShopfloorService._team_detail(db, team)

    @staticmethod
    async def member_status(db: AsyncSession, team_id: int, member_id: int, obj: StatusInput) -> TeamDetail:
        team = await ShopfloorService._team(db, team_id, True)
        member = await db.scalar(select(ProductionTeamMember).where(ProductionTeamMember.id == member_id, ProductionTeamMember.team_id == team.id, ProductionTeamMember.deleted == 0).with_for_update())
        if not member:
            raise errors.NotFoundError(msg='TEAM_MEMBER_NOT_FOUND')
        member.status = obj.status
        member.updated_by = ShopfloorService.user_id()
        await db.flush()
        return await ShopfloorService._team_detail(db, team)

    @staticmethod
    async def _station(db: AsyncSession, workstation_id: int, lock: bool = False) -> Workstation:
        stmt = select(Workstation).where(Workstation.id == workstation_id, Workstation.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='WORKSTATION_NOT_FOUND')
        return row

    @staticmethod
    async def _validate_station_refs(db: AsyncSession, obj: WorkstationInput) -> None:
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == obj.work_center_id, WorkCenter.deleted == 0, WorkCenter.status == WorkCenterStatus.ACTIVE))
        if not center or not center.production_enabled:
            raise errors.ConflictError(msg='WORK_CENTER_NOT_PRODUCTION_ENABLED')
        if obj.equipment_id:
            equipment = await db.scalar(select(Equipment).where(Equipment.id == obj.equipment_id, Equipment.deleted == 0))
            if not equipment or not equipment.enabled or not equipment.production_enabled:
                raise errors.ConflictError(msg='WORKSTATION_EQUIPMENT_INVALID')

    @staticmethod
    async def _station_detail(db: AsyncSession, row: Workstation) -> WorkstationDetail:
        center = await db.scalar(select(WorkCenter).where(WorkCenter.id == row.work_center_id, WorkCenter.deleted == 0))
        equipment = await db.scalar(select(Equipment).where(Equipment.id == row.equipment_id, Equipment.deleted == 0)) if row.equipment_id else None
        result = WorkstationDetail.model_validate(row)
        result.work_center_code = center.work_center_code if center else ''
        result.work_center_name = center.work_center_name if center else ''
        result.equipment_code = equipment.equipment_code if equipment else None
        result.equipment_name = equipment.equipment_name if equipment else None
        return result

    @staticmethod
    async def list_workstations(db: AsyncSession) -> list[WorkstationDetail]:
        rows = (await db.scalars(select(Workstation).where(Workstation.deleted == 0).order_by(Workstation.workstation_code))).all()
        return [await ShopfloorService._station_detail(db, row) for row in rows]

    @staticmethod
    async def create_workstation(db: AsyncSession, obj: WorkstationInput) -> WorkstationDetail:
        await ShopfloorService._validate_station_refs(db, obj)
        if await db.scalar(select(Workstation.id).where(Workstation.workstation_code == obj.workstation_code, Workstation.deleted == 0)):
            raise errors.ConflictError(msg='WORKSTATION_CODE_EXISTS')
        row = Workstation(**obj.model_dump())
        row.created_by = ShopfloorService.user_id()
        db.add(row)
        await db.flush()
        return await ShopfloorService._station_detail(db, row)

    @staticmethod
    async def update_workstation(db: AsyncSession, workstation_id: int, obj: WorkstationInput) -> WorkstationDetail:
        row = await ShopfloorService._station(db, workstation_id, True)
        await ShopfloorService._validate_station_refs(db, obj)
        duplicate = await db.scalar(select(Workstation.id).where(Workstation.workstation_code == obj.workstation_code, Workstation.id != row.id, Workstation.deleted == 0))
        if duplicate:
            raise errors.ConflictError(msg='WORKSTATION_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(row, key, value)
        row.updated_by = ShopfloorService.user_id()
        await db.flush()
        return await ShopfloorService._station_detail(db, row)

    @staticmethod
    async def workstation_status(db: AsyncSession, workstation_id: int, obj: StatusInput) -> WorkstationDetail:
        row = await ShopfloorService._station(db, workstation_id, True)
        row.status = obj.status
        row.updated_by = ShopfloorService.user_id()
        await db.flush()
        return await ShopfloorService._station_detail(db, row)

    @staticmethod
    async def workstation_options(db: AsyncSession) -> list[WorkstationOption]:
        rows = (await db.scalars(select(Workstation).where(Workstation.deleted == 0, Workstation.status == ShopfloorStatus.ACTIVE).order_by(Workstation.workstation_code))).all()
        return [WorkstationOption(id=row.id, code=row.workstation_code, name=row.workstation_name, work_center_id=row.work_center_id) for row in rows]

    @staticmethod
    async def check_in(db: AsyncSession, workstation_id: int, obj: CheckInInput) -> WorkstationSessionDetail:
        user_id = ShopfloorService.user_id()
        station = await ShopfloorService._station(db, workstation_id, True)
        if station.status != ShopfloorStatus.ACTIVE or not station.terminal_enabled:
            raise errors.ConflictError(msg='WORKSTATION_DISABLED')
        current = await db.scalar(select(WorkstationSession).where(WorkstationSession.user_id == user_id, WorkstationSession.status == WorkstationSessionStatus.ACTIVE, WorkstationSession.deleted == 0).with_for_update())
        if current:
            if current.workstation_id == station.id and current.team_id == obj.team_id:
                return WorkstationSessionDetail.model_validate(current)
            raise errors.ConflictError(msg='OPERATOR_ALREADY_CHECKED_IN')
        if obj.team_id:
            team = await ShopfloorService._team(db, obj.team_id)
            if team.status != ShopfloorStatus.ACTIVE or (team.work_center_id and team.work_center_id != station.work_center_id):
                raise errors.ConflictError(msg='PRODUCTION_TEAM_CENTER_MISMATCH')
            member = await db.scalar(select(ProductionTeamMember.id).where(ProductionTeamMember.team_id == team.id, ProductionTeamMember.user_id == user_id, ProductionTeamMember.status == ShopfloorStatus.ACTIVE, ProductionTeamMember.deleted == 0))
            if not member:
                raise errors.ConflictError(msg='OPERATOR_NOT_TEAM_MEMBER')
        now = timezone.now()
        row = WorkstationSession(workstation_id=station.id, user_id=user_id, team_id=obj.team_id, signed_in_at=now, last_activity_at=now)
        row.created_by = user_id
        db.add(row)
        await db.flush()
        return WorkstationSessionDetail.model_validate(row)

    @staticmethod
    async def check_out(db: AsyncSession, session_id: int) -> WorkstationSessionDetail:
        row = await db.scalar(select(WorkstationSession).where(WorkstationSession.id == session_id, WorkstationSession.user_id == ShopfloorService.user_id(), WorkstationSession.deleted == 0).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='WORKSTATION_SESSION_NOT_FOUND')
        if row.status == WorkstationSessionStatus.ACTIVE:
            row.status = WorkstationSessionStatus.CLOSED
            row.signed_out_at = timezone.now()
            row.last_activity_at = row.signed_out_at
            await db.flush()
        return WorkstationSessionDetail.model_validate(row)

    @staticmethod
    async def terminal_context(db: AsyncSession, workstation_id: int) -> TerminalContext:
        station = await ShopfloorService._station(db, workstation_id)
        detail = await ShopfloorService._station_detail(db, station)
        user_id = ShopfloorService.user_id()
        session = await db.scalar(select(WorkstationSession).where(WorkstationSession.workstation_id == station.id, WorkstationSession.user_id == user_id, WorkstationSession.status == WorkstationSessionStatus.ACTIVE, WorkstationSession.deleted == 0))
        stmt = select(ApsDispatch, ApsOperationSchedule).join(ApsOperationSchedule, ApsOperationSchedule.id == ApsDispatch.schedule_operation_id).where(ApsDispatch.work_center_id == station.work_center_id, ApsDispatch.status.in_([DispatchStatus.DISPATCHED, DispatchStatus.ACCEPTED, DispatchStatus.STARTED]), ApsDispatch.deleted == 0, ApsOperationSchedule.deleted == 0)
        stmt = stmt.where((ApsDispatch.workstation_id.is_(None)) | (ApsDispatch.workstation_id == station.id))
        rows = (await db.execute(stmt.order_by(ApsDispatch.priority.desc(), ApsDispatch.planned_start_at))).all()
        dispatches = [TerminalDispatchDetail(id=row.id, dispatch_no=row.dispatch_no, work_order_id=row.work_order_id, work_order_no=line.work_order_no_snapshot, work_order_operation_id=row.work_order_operation_id, operation_name=line.operation_name_snapshot, dispatch_quantity=row.dispatch_quantity, status=row.status, planned_start_at=row.planned_start_at, planned_end_at=row.planned_end_at, assigned_team=row.assigned_team, workstation_code=row.workstation_code, production_execution_id=row.production_execution_id) for row, line in rows if row.assigned_user_id in (None, user_id)]
        return TerminalContext(workstation=detail, session=WorkstationSessionDetail.model_validate(session) if session else None, dispatches=dispatches)

    @staticmethod
    async def _active_session(db: AsyncSession, workstation_id: int) -> WorkstationSession:
        row = await db.scalar(select(WorkstationSession).where(WorkstationSession.workstation_id == workstation_id, WorkstationSession.user_id == ShopfloorService.user_id(), WorkstationSession.status == WorkstationSessionStatus.ACTIVE, WorkstationSession.deleted == 0).with_for_update())
        if not row:
            raise errors.ConflictError(msg='OPERATOR_NOT_CHECKED_IN')
        return row

    @staticmethod
    async def start_dispatch(db: AsyncSession, dispatch_id: int, workstation_id: int) -> TerminalDispatchDetail:
        session = await ShopfloorService._active_session(db, workstation_id)
        row = await db.scalar(select(ApsDispatch).where(ApsDispatch.id == dispatch_id, ApsDispatch.deleted == 0).with_for_update())
        if not row or row.status not in (DispatchStatus.DISPATCHED, DispatchStatus.ACCEPTED):
            raise errors.ConflictError(msg='DISPATCH_NOT_STARTABLE')
        if row.workstation_id and row.workstation_id != workstation_id:
            raise errors.ConflictError(msg='DISPATCH_WORKSTATION_MISMATCH')
        if row.assigned_user_id and row.assigned_user_id != session.user_id:
            raise errors.ConflictError(msg='DISPATCH_OPERATOR_MISMATCH')
        if row.team_id and row.team_id != session.team_id:
            raise errors.ConflictError(msg='DISPATCH_TEAM_MISMATCH')
        execution = await production_execution_service.start(db, row.work_order_id, row.work_order_operation_id, StartProductionExecution(remark=f'Dispatch {row.dispatch_no}'))
        row.status = DispatchStatus.STARTED
        row.accepted_at = row.accepted_at or timezone.now()
        row.accepted_by = row.accepted_by or session.user_id
        row.workstation_id = workstation_id
        row.production_execution_id = execution.id
        session.last_activity_at = timezone.now()
        line = await db.scalar(select(ApsOperationSchedule).where(ApsOperationSchedule.id == row.schedule_operation_id, ApsOperationSchedule.deleted == 0).with_for_update())
        if line:
            line.status = OperationScheduleStatus.IN_PROGRESS
        await db.flush()
        context = await ShopfloorService.terminal_context(db, workstation_id)
        return next(item for item in context.dispatches if item.id == row.id)

    @staticmethod
    async def complete_dispatch(db: AsyncSession, dispatch_id: int, workstation_id: int, obj: CompleteDispatchInput) -> TerminalDispatchDetail:
        session = await ShopfloorService._active_session(db, workstation_id)
        row = await db.scalar(select(ApsDispatch).where(ApsDispatch.id == dispatch_id, ApsDispatch.deleted == 0).with_for_update())
        if not row or row.status != DispatchStatus.STARTED or not row.production_execution_id:
            raise errors.ConflictError(msg='DISPATCH_NOT_COMPLETABLE')
        if row.workstation_id != workstation_id:
            raise errors.ConflictError(msg='DISPATCH_WORKSTATION_MISMATCH')
        if obj.good_quantity + obj.scrap_quantity > Decimal(row.dispatch_quantity):
            raise errors.ConflictError(msg='DISPATCH_COMPLETION_QUANTITY_INVALID')
        await production_execution_service.complete(db, row.production_execution_id, CompleteProductionExecution(good_quantity=obj.good_quantity, scrap_quantity=obj.scrap_quantity, remark=obj.remark))
        row.status = DispatchStatus.COMPLETED
        session.last_activity_at = timezone.now()
        line = await db.scalar(select(ApsOperationSchedule).where(ApsOperationSchedule.id == row.schedule_operation_id, ApsOperationSchedule.deleted == 0).with_for_update())
        remaining = await db.scalar(select(func.count(ApsDispatch.id)).where(ApsDispatch.schedule_operation_id == row.schedule_operation_id, ApsDispatch.id != row.id, ApsDispatch.status.not_in([DispatchStatus.COMPLETED, DispatchStatus.CANCELLED]), ApsDispatch.deleted == 0))
        if not remaining:
            if line:
                line.status = OperationScheduleStatus.COMPLETED
        await db.flush()
        return TerminalDispatchDetail(id=row.id, dispatch_no=row.dispatch_no, work_order_id=row.work_order_id, work_order_no=line.work_order_no_snapshot if line else '', work_order_operation_id=row.work_order_operation_id, operation_name=line.operation_name_snapshot if line else '', dispatch_quantity=row.dispatch_quantity, status=row.status, planned_start_at=row.planned_start_at, planned_end_at=row.planned_end_at, assigned_team=row.assigned_team, workstation_code=row.workstation_code, production_execution_id=row.production_execution_id)


shopfloor_service = ShopfloorService()
