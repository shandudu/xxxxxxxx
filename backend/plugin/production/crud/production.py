from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.production.model import MaterialIssue, MaterialIssueLine, WorkOrder, WorkOrderMaterialRequirement, WorkOrderOperation


class ProductionRepository:
    async def list_orders(self, db: AsyncSession, status: str | None = None) -> Sequence[WorkOrder]:
        statement = select(WorkOrder).where(WorkOrder.deleted == 0)
        if status:
            statement = statement.where(WorkOrder.status == status)
        return (await db.scalars(statement.order_by(WorkOrder.created_time.desc(), WorkOrder.id.desc()))).all()

    async def get_order(self, db: AsyncSession, order_id: int, lock: bool = False) -> WorkOrder | None:
        statement = select(WorkOrder).where(WorkOrder.id == order_id, WorkOrder.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def get_order_by_no(self, db: AsyncSession, number: str) -> WorkOrder | None:
        return await db.scalar(select(WorkOrder).where(WorkOrder.work_order_no == number, WorkOrder.deleted == 0))

    async def operations(self, db: AsyncSession, order_id: int) -> Sequence[WorkOrderOperation]:
        return (await db.scalars(select(WorkOrderOperation).where(WorkOrderOperation.work_order_id == order_id, WorkOrderOperation.deleted == 0).order_by(WorkOrderOperation.sequence_no))).all()

    async def requirements(self, db: AsyncSession, order_id: int) -> Sequence[WorkOrderMaterialRequirement]:
        return (await db.scalars(select(WorkOrderMaterialRequirement).where(WorkOrderMaterialRequirement.work_order_id == order_id, WorkOrderMaterialRequirement.deleted == 0).order_by(WorkOrderMaterialRequirement.line_no))).all()

    async def requirement(self, db: AsyncSession, requirement_id: int, lock: bool = False) -> WorkOrderMaterialRequirement | None:
        statement = select(WorkOrderMaterialRequirement).where(WorkOrderMaterialRequirement.id == requirement_id, WorkOrderMaterialRequirement.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def issue_line(self, db: AsyncSession, line_id: int, lock: bool = False) -> MaterialIssueLine | None:
        statement = select(MaterialIssueLine).where(MaterialIssueLine.id == line_id, MaterialIssueLine.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def issues(self, db: AsyncSession, order_id: int) -> Sequence[MaterialIssue]:
        return (await db.scalars(select(MaterialIssue).where(MaterialIssue.work_order_id == order_id, MaterialIssue.deleted == 0).order_by(MaterialIssue.created_time.desc()))).all()

    async def issue_lines(self, db: AsyncSession, issue_id: int) -> Sequence[MaterialIssueLine]:
        return (await db.scalars(select(MaterialIssueLine).where(MaterialIssueLine.issue_id == issue_id, MaterialIssueLine.deleted == 0).order_by(MaterialIssueLine.id))).all()


production_repo = ProductionRepository()
