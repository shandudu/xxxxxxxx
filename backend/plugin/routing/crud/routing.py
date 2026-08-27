from datetime import datetime
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.routing.enums import (
    OperationStatus,
    OperationType,
    RoutingStatus,
    RoutingType,
    WorkCenterStatus,
    WorkCenterType,
)
from backend.plugin.routing.model import Operation, Routing, RoutingOperation, WorkCenter


class RoutingRepository:
    async def get_operation(self, db: AsyncSession, operation_id: int) -> Operation | None:
        return await db.scalar(select(Operation).where(Operation.id == operation_id, Operation.deleted == 0))

    async def get_operation_by_code(
        self, db: AsyncSession, operation_code: str, exclude_id: int | None = None
    ) -> Operation | None:
        statement = select(Operation).where(Operation.operation_code == operation_code, Operation.deleted == 0)
        if exclude_id:
            statement = statement.where(Operation.id != exclude_id)
        return await db.scalar(statement)

    async def create_operation(self, db: AsyncSession, data: dict) -> Operation:
        item = Operation(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_operation_select(
        self, keyword: str | None, operation_type: OperationType | None, status: OperationStatus | None
    ):
        statement = select(Operation).where(Operation.deleted == 0)
        if keyword:
            statement = statement.where(
                or_(Operation.operation_code.contains(keyword), Operation.operation_name.contains(keyword))
            )
        if operation_type:
            statement = statement.where(Operation.operation_type == operation_type)
        if status:
            statement = statement.where(Operation.status == status)
        return statement.order_by(Operation.sort_no, Operation.id.desc())

    async def get_work_center(self, db: AsyncSession, work_center_id: int) -> WorkCenter | None:
        return await db.scalar(select(WorkCenter).where(WorkCenter.id == work_center_id, WorkCenter.deleted == 0))

    async def get_work_center_by_code(
        self, db: AsyncSession, work_center_code: str, exclude_id: int | None = None
    ) -> WorkCenter | None:
        statement = select(WorkCenter).where(WorkCenter.work_center_code == work_center_code, WorkCenter.deleted == 0)
        if exclude_id:
            statement = statement.where(WorkCenter.id != exclude_id)
        return await db.scalar(statement)

    async def create_work_center(self, db: AsyncSession, data: dict) -> WorkCenter:
        item = WorkCenter(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_work_center_select(
        self, keyword: str | None, work_center_type: WorkCenterType | None, status: WorkCenterStatus | None
    ):
        statement = select(WorkCenter).where(WorkCenter.deleted == 0)
        if keyword:
            statement = statement.where(
                or_(WorkCenter.work_center_code.contains(keyword), WorkCenter.work_center_name.contains(keyword))
            )
        if work_center_type:
            statement = statement.where(WorkCenter.work_center_type == work_center_type)
        if status:
            statement = statement.where(WorkCenter.status == status)
        return statement.order_by(WorkCenter.sort_no, WorkCenter.id.desc())

    async def get_routing(self, db: AsyncSession, routing_id: int) -> Routing | None:
        return await db.scalar(select(Routing).where(Routing.id == routing_id, Routing.deleted == 0))

    async def get_routing_by_code(
        self, db: AsyncSession, routing_code: str, exclude_id: int | None = None
    ) -> Routing | None:
        statement = select(Routing).where(Routing.routing_code == routing_code, Routing.deleted == 0)
        if exclude_id:
            statement = statement.where(Routing.id != exclude_id)
        return await db.scalar(statement)

    async def get_routing_by_product_version(
        self,
        db: AsyncSession,
        product_material_id: int,
        routing_version: str,
        routing_type: RoutingType,
        exclude_id: int | None = None,
    ) -> Routing | None:
        statement = select(Routing).where(
            Routing.product_material_id == product_material_id,
            Routing.routing_version == routing_version,
            Routing.routing_type == routing_type,
            Routing.deleted == 0,
        )
        if exclude_id:
            statement = statement.where(Routing.id != exclude_id)
        return await db.scalar(statement)

    async def create_routing(self, db: AsyncSession, data: dict) -> Routing:
        item = Routing(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_routing_select(
        self,
        keyword: str | None,
        product_material_id: int | None,
        status: RoutingStatus | None,
        routing_type: RoutingType | None,
        is_default: bool | None,
        effective_date: datetime | None,
    ):
        statement = select(Routing).where(Routing.deleted == 0)
        if keyword:
            statement = statement.where(
                or_(Routing.routing_code.contains(keyword), Routing.routing_name.contains(keyword))
            )
        if product_material_id:
            statement = statement.where(Routing.product_material_id == product_material_id)
        if status:
            statement = statement.where(Routing.status == status)
        if routing_type:
            statement = statement.where(Routing.routing_type == routing_type)
        if is_default is not None:
            statement = statement.where(Routing.is_default == is_default)
        if effective_date:
            statement = statement.where(
                (Routing.effective_from.is_(None)) | (Routing.effective_from <= effective_date),
                (Routing.effective_to.is_(None)) | (Routing.effective_to >= effective_date),
            )
        return statement.order_by(
            Routing.product_material_id, Routing.routing_type, Routing.is_default.desc(), Routing.routing_version.desc(), Routing.id.desc()
        )

    async def get_operations(self, db: AsyncSession, routing_id: int) -> Sequence[RoutingOperation]:
        return (
            await db.scalars(
                select(RoutingOperation)
                .where(RoutingOperation.routing_id == routing_id, RoutingOperation.deleted == 0)
                .order_by(RoutingOperation.sequence_no, RoutingOperation.id)
            )
        ).all()

    async def get_routing_operation(
        self, db: AsyncSession, routing_id: int, routing_operation_id: int
    ) -> RoutingOperation | None:
        return await db.scalar(
            select(RoutingOperation).where(
                RoutingOperation.id == routing_operation_id,
                RoutingOperation.routing_id == routing_id,
                RoutingOperation.deleted == 0,
            )
        )

    async def get_routing_operation_by_sequence(
        self, db: AsyncSession, routing_id: int, sequence_no: int, exclude_id: int | None = None
    ) -> RoutingOperation | None:
        statement = select(RoutingOperation).where(
            RoutingOperation.routing_id == routing_id,
            RoutingOperation.sequence_no == sequence_no,
            RoutingOperation.deleted == 0,
        )
        if exclude_id:
            statement = statement.where(RoutingOperation.id != exclude_id)
        return await db.scalar(statement)

    async def create_routing_operation(self, db: AsyncSession, data: dict) -> RoutingOperation:
        item = RoutingOperation(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_operation_count_map(self, db: AsyncSession, routing_ids: set[int]) -> dict[int, int]:
        if not routing_ids:
            return {}
        rows = await db.execute(
            select(RoutingOperation.routing_id, func.count(RoutingOperation.id))
            .where(RoutingOperation.routing_id.in_(routing_ids), RoutingOperation.deleted == 0)
            .group_by(RoutingOperation.routing_id)
        )
        return {routing_id: count for routing_id, count in rows.all()}


routing_repo = RoutingRepository()
