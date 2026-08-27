from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.production.enums import (
    ProductionExecutionStatus,
    WorkOrderOperationStatus,
    WorkOrderStatus,
)
from backend.plugin.production.model import (
    MaterialConsumption,
    MaterialIssueLine,
    ProductionExecution,
    WorkOrder,
    WorkOrderMaterialRequirement,
    WorkOrderMaterialAllocation,
    WorkOrderOperation,
)
from backend.plugin.production.schema.execution import (
    CompleteProductionExecution,
    MaterialConsumptionDetail,
    ProductionExecutionDetail,
    RecordMaterialConsumption,
    StartProductionExecution,
)
from backend.utils.timezone import timezone


class ProductionExecutionService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _execution(db: AsyncSession, execution_id: int, *, lock: bool = False) -> ProductionExecution:
        stmt = select(ProductionExecution).where(ProductionExecution.id == execution_id, ProductionExecution.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        execution = await db.scalar(stmt)
        if not execution:
            raise errors.NotFoundError(msg='PRODUCTION_EXECUTION_NOT_FOUND')
        return execution

    @staticmethod
    async def consumptions(db: AsyncSession, execution_id: int) -> list[MaterialConsumption]:
        return list((await db.scalars(
            select(MaterialConsumption)
            .where(MaterialConsumption.execution_id == execution_id, MaterialConsumption.deleted == 0)
            .order_by(MaterialConsumption.consumed_at, MaterialConsumption.id)
        )).all())

    @staticmethod
    async def detail(db: AsyncSession, execution: ProductionExecution) -> ProductionExecutionDetail:
        result = ProductionExecutionDetail.model_validate(execution)
        result.consumptions = [MaterialConsumptionDetail.model_validate(item) for item in await ProductionExecutionService.consumptions(db, execution.id)]
        return result

    @staticmethod
    async def list_for_order(db: AsyncSession, order_id: int) -> list[ProductionExecutionDetail]:
        if not await db.scalar(select(WorkOrder.id).where(WorkOrder.id == order_id, WorkOrder.deleted == 0)):
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        rows = (await db.scalars(
            select(ProductionExecution)
            .where(ProductionExecution.work_order_id == order_id, ProductionExecution.deleted == 0)
            .order_by(ProductionExecution.started_at.desc())
        )).all()
        return [await ProductionExecutionService.detail(db, item) for item in rows]

    @staticmethod
    async def get(db: AsyncSession, execution_id: int) -> ProductionExecutionDetail:
        return await ProductionExecutionService.detail(db, await ProductionExecutionService._execution(db, execution_id))

    @staticmethod
    async def start(
        db: AsyncSession,
        order_id: int,
        operation_id: int,
        obj: StartProductionExecution,
    ) -> ProductionExecutionDetail:
        order = await db.scalar(select(WorkOrder).where(WorkOrder.id == order_id, WorkOrder.deleted == 0).with_for_update())
        if not order or order.status not in (WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS):
            raise errors.ConflictError(msg='WORK_ORDER_NOT_EXECUTABLE')
        operation = await db.scalar(
            select(WorkOrderOperation)
            .where(WorkOrderOperation.id == operation_id, WorkOrderOperation.work_order_id == order_id, WorkOrderOperation.deleted == 0)
            .with_for_update()
        )
        if not operation:
            raise errors.NotFoundError(msg='WORK_ORDER_OPERATION_NOT_FOUND')
        if operation.status in (WorkOrderOperationStatus.COMPLETED, WorkOrderOperationStatus.SKIPPED):
            raise errors.ConflictError(msg='WORK_ORDER_OPERATION_CLOSED')
        previous_open = await db.scalar(
            select(WorkOrderOperation.id).where(
                WorkOrderOperation.work_order_id == order_id,
                WorkOrderOperation.sequence_no < operation.sequence_no,
                WorkOrderOperation.status.not_in((WorkOrderOperationStatus.COMPLETED, WorkOrderOperationStatus.SKIPPED)),
                WorkOrderOperation.deleted == 0,
            )
        )
        if previous_open:
            raise errors.ConflictError(msg='PREVIOUS_OPERATION_NOT_COMPLETED')
        active = await db.scalar(
            select(ProductionExecution.id).where(
                ProductionExecution.work_order_operation_id == operation.id,
                ProductionExecution.status == ProductionExecutionStatus.IN_PROGRESS,
                ProductionExecution.deleted == 0,
            )
        )
        if active:
            raise errors.ConflictError(msg='OPERATION_EXECUTION_ALREADY_IN_PROGRESS')
        now = timezone.now()
        execution = ProductionExecution(
            execution_no=(obj.execution_no or f'EXE-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper(),
            work_order_id=order.id,
            work_order_operation_id=operation.id,
            started_at=now,
            operator_id=ProductionExecutionService._operator_id(),
            remark=obj.remark,
        )
        db.add(execution)
        operation.status = WorkOrderOperationStatus.IN_PROGRESS
        operation.started_at = operation.started_at or now
        if order.status == WorkOrderStatus.RELEASED:
            order.status = WorkOrderStatus.IN_PROGRESS
            order.started_at = order.started_at or now
        await db.flush()
        return await ProductionExecutionService.detail(db, execution)

    @staticmethod
    async def consume(
        db: AsyncSession,
        execution_id: int,
        obj: RecordMaterialConsumption,
    ) -> MaterialConsumption:
        execution = await ProductionExecutionService._execution(db, execution_id, lock=True)
        if execution.status != ProductionExecutionStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='PRODUCTION_EXECUTION_NOT_IN_PROGRESS')
        requirement = await db.scalar(
            select(WorkOrderMaterialRequirement)
            .where(
                WorkOrderMaterialRequirement.id == obj.requirement_id,
                WorkOrderMaterialRequirement.work_order_id == execution.work_order_id,
                WorkOrderMaterialRequirement.deleted == 0,
            )
            .with_for_update()
        )
        if not requirement:
            raise errors.NotFoundError(msg='WORK_ORDER_REQUIREMENT_NOT_FOUND')
        if requirement.work_order_operation_id not in (None, execution.work_order_operation_id):
            raise errors.ConflictError(msg='REQUIREMENT_OPERATION_MISMATCH')
        allocation_count = await db.scalar(
            select(func.count(WorkOrderMaterialAllocation.id)).where(
                WorkOrderMaterialAllocation.requirement_id == requirement.id,
                WorkOrderMaterialAllocation.deleted == 0,
            )
        )
        if allocation_count and not await db.scalar(
            select(WorkOrderMaterialAllocation.id).where(
                WorkOrderMaterialAllocation.requirement_id == requirement.id,
                WorkOrderMaterialAllocation.work_order_operation_id == execution.work_order_operation_id,
                WorkOrderMaterialAllocation.deleted == 0,
            )
        ):
            raise errors.ConflictError(msg='REQUIREMENT_OPERATION_MISMATCH')
        issue_line = None
        if obj.issue_line_id:
            issue_line = await db.scalar(
                select(MaterialIssueLine).where(
                    MaterialIssueLine.id == obj.issue_line_id,
                    MaterialIssueLine.requirement_id == requirement.id,
                    MaterialIssueLine.deleted == 0,
                )
            )
            if not issue_line:
                raise errors.NotFoundError(msg='MATERIAL_ISSUE_LINE_NOT_FOUND')
            consumed_from_line = await db.scalar(
                select(func.coalesce(func.sum(MaterialConsumption.quantity), 0)).where(
                    MaterialConsumption.issue_line_id == issue_line.id,
                    MaterialConsumption.deleted == 0,
                )
            )
            if Decimal(consumed_from_line) + obj.quantity > issue_line.quantity - issue_line.returned_quantity:
                raise errors.ConflictError(msg='CONSUMPTION_EXCEEDS_AVAILABLE_ISSUE_LINE')
        consumed = await db.scalar(
            select(func.coalesce(func.sum(MaterialConsumption.quantity), 0)).where(
                MaterialConsumption.requirement_id == requirement.id,
                MaterialConsumption.deleted == 0,
            )
        )
        if Decimal(consumed) + obj.quantity > requirement.issued_quantity - requirement.returned_quantity:
            raise errors.ConflictError(msg='CONSUMPTION_EXCEEDS_NET_ISSUED_QUANTITY')
        now = timezone.now()
        row = MaterialConsumption(
            consumption_no=(obj.consumption_no or f'CON-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper(),
            execution_id=execution.id,
            requirement_id=requirement.id,
            issue_line_id=issue_line.id if issue_line else None,
            material_id=requirement.material_id,
            lot_id=issue_line.lot_id if issue_line else None,
            quantity=obj.quantity,
            consumed_at=now,
            operator_id=ProductionExecutionService._operator_id(),
            remark=obj.remark,
        )
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def complete(
        db: AsyncSession,
        execution_id: int,
        obj: CompleteProductionExecution,
    ) -> ProductionExecutionDetail:
        execution = await ProductionExecutionService._execution(db, execution_id, lock=True)
        if execution.status != ProductionExecutionStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='PRODUCTION_EXECUTION_NOT_IN_PROGRESS')
        operation = await db.scalar(
            select(WorkOrderOperation)
            .where(WorkOrderOperation.id == execution.work_order_operation_id, WorkOrderOperation.deleted == 0)
            .with_for_update()
        )
        order = await db.scalar(select(WorkOrder).where(WorkOrder.id == execution.work_order_id, WorkOrder.deleted == 0))
        if not operation or not order:
            raise errors.ConflictError(msg='PRODUCTION_EXECUTION_SNAPSHOT_MISSING')
        if operation.completed_quantity + obj.good_quantity > order.planned_quantity:
            raise errors.ConflictError(msg='OPERATION_COMPLETION_EXCEEDS_PLANNED_QUANTITY')
        now = timezone.now()
        execution.status = ProductionExecutionStatus.COMPLETED
        execution.good_quantity = obj.good_quantity
        execution.scrap_quantity = obj.scrap_quantity
        execution.completed_at = now
        execution.remark = obj.remark or execution.remark
        operation.completed_quantity += obj.good_quantity
        operation.scrap_quantity += obj.scrap_quantity
        if operation.completed_quantity >= order.planned_quantity:
            operation.status = WorkOrderOperationStatus.COMPLETED
            operation.completed_at = now
        await db.flush()
        return await ProductionExecutionService.detail(db, execution)


production_execution_service = ProductionExecutionService()
