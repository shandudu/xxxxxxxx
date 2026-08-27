from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.planning.model import MpsDemand, MpsPlan, MrpRequirement, MrpRun, PlannedOrder


class PlanningRepository:
    async def list_plans(self, db: AsyncSession, status: str | None = None) -> Sequence[MpsPlan]:
        statement = select(MpsPlan).where(MpsPlan.deleted == 0)
        if status:
            statement = statement.where(MpsPlan.status == status)
        return (await db.scalars(statement.order_by(MpsPlan.created_time.desc(), MpsPlan.id.desc()))).all()

    async def get_plan(self, db: AsyncSession, plan_id: int, *, lock: bool = False) -> MpsPlan | None:
        statement = select(MpsPlan).where(MpsPlan.id == plan_id, MpsPlan.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def get_plan_by_no(self, db: AsyncSession, plan_no: str) -> MpsPlan | None:
        return await db.scalar(select(MpsPlan).where(MpsPlan.plan_no == plan_no, MpsPlan.deleted == 0))

    async def demands(self, db: AsyncSession, plan_id: int) -> Sequence[MpsDemand]:
        statement = (
            select(MpsDemand)
            .where(MpsDemand.mps_plan_id == plan_id, MpsDemand.deleted == 0)
            .order_by(MpsDemand.demand_date, MpsDemand.line_no)
        )
        return (await db.scalars(statement)).all()

    async def get_demand(self, db: AsyncSession, demand_id: int, *, lock: bool = False) -> MpsDemand | None:
        statement = select(MpsDemand).where(MpsDemand.id == demand_id, MpsDemand.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def list_runs(self, db: AsyncSession, plan_id: int | None = None) -> Sequence[MrpRun]:
        statement = select(MrpRun).where(MrpRun.deleted == 0)
        if plan_id:
            statement = statement.where(MrpRun.mps_plan_id == plan_id)
        return (await db.scalars(statement.order_by(MrpRun.created_time.desc(), MrpRun.id.desc()))).all()

    async def get_run(self, db: AsyncSession, run_id: int) -> MrpRun | None:
        return await db.scalar(select(MrpRun).where(MrpRun.id == run_id, MrpRun.deleted == 0))

    async def requirements(self, db: AsyncSession, run_id: int) -> Sequence[MrpRequirement]:
        statement = (
            select(MrpRequirement)
            .where(MrpRequirement.mrp_run_id == run_id, MrpRequirement.deleted == 0)
            .order_by(MrpRequirement.sequence_no)
        )
        return (await db.scalars(statement)).all()

    async def planned_orders(self, db: AsyncSession, run_id: int) -> Sequence[PlannedOrder]:
        statement = (
            select(PlannedOrder)
            .where(PlannedOrder.mrp_run_id == run_id, PlannedOrder.deleted == 0)
            .order_by(PlannedOrder.sequence_no)
        )
        return (await db.scalars(statement)).all()

    async def get_planned_order(
        self, db: AsyncSession, planned_order_id: int, *, lock: bool = False
    ) -> PlannedOrder | None:
        statement = select(PlannedOrder).where(PlannedOrder.id == planned_order_id, PlannedOrder.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)


planning_repo = PlanningRepository()
