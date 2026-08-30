from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom, BomItem
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.service import inventory_service
from backend.plugin.material.model import Material
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
from backend.plugin.operation_material.model import OperationMaterialPlan, OperationMaterialRequirement
from backend.plugin.production.crud import production_repo
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import (
    MaterialIssue, MaterialIssueLine, MaterialReturn, MaterialReturnLine, ProductionReport,
    WorkOrder, WorkOrderMaterialRequirement, WorkOrderOperation,
    WorkOrderMaterialAllocation,
)
from backend.plugin.production.schema.production import (
    CreateMaterialIssue, CreateMaterialReturn, CreateProductionReport, CreateWorkOrder,
    MaterialIssueDetail, MaterialIssueLineDetail, WorkOrderDetail, WorkOrderOperationDetail, WorkOrderRequirementDetail,
    MaterialVarianceDetail, ProductionDashboard,
    WorkOrderMaterialAllocationDetail,
)
from backend.plugin.routing.enums import RoutingStatus
from backend.plugin.routing.model import Operation, Routing, RoutingOperation
from backend.plugin.trace.enums import LotSourceType, LotType, QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.utils.timezone import timezone


class ProductionService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _detail(
        order: WorkOrder,
        operations: Sequence[WorkOrderOperation],
        requirements: Sequence[WorkOrderMaterialRequirement],
        allocations: Sequence[WorkOrderMaterialAllocation] = (),
    ) -> WorkOrderDetail:
        detail = WorkOrderDetail.model_validate(order)
        detail.operations = [WorkOrderOperationDetail.model_validate(item) for item in operations]
        detail.requirements = [WorkOrderRequirementDetail.model_validate(item) for item in requirements]
        detail.material_allocations = [WorkOrderMaterialAllocationDetail.model_validate(item) for item in allocations]
        return detail

    @staticmethod
    async def list_orders(db: AsyncSession, status: str | None = None) -> Sequence[WorkOrder]:
        return await production_repo.list_orders(db, status)

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int) -> WorkOrderDetail:
        order = await production_repo.get_order(db, order_id)
        if not order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        allocations = (await db.scalars(
            select(WorkOrderMaterialAllocation)
            .where(WorkOrderMaterialAllocation.work_order_id == order.id, WorkOrderMaterialAllocation.deleted == 0)
            .order_by(WorkOrderMaterialAllocation.id)
        )).all()
        return ProductionService._detail(
            order,
            await production_repo.operations(db, order.id),
            await production_repo.requirements(db, order.id),
            allocations,
        )

    @staticmethod
    async def material_variance(db: AsyncSession, order_id: int) -> list[MaterialVarianceDetail]:
        await ProductionService.get_order(db, order_id)
        result = []
        for item in await production_repo.requirements(db, order_id):
            actual = item.issued_quantity - item.returned_quantity
            variance = actual - item.required_quantity
            rate = (variance / item.required_quantity * Decimal('100')) if item.required_quantity else None
            result.append(MaterialVarianceDetail(
                requirement_id=item.id, material_id=item.material_id,
                material_code=item.material_code_snapshot, material_name=item.material_name_snapshot,
                required_quantity=item.required_quantity, issued_quantity=item.issued_quantity,
                returned_quantity=item.returned_quantity, actual_quantity=actual,
                variance_quantity=variance, variance_rate=rate,
            ))
        return result

    @staticmethod
    async def dashboard(db: AsyncSession) -> ProductionDashboard:
        orders = list(await production_repo.list_orders(db))
        planned = sum((item.planned_quantity for item in orders), Decimal('0'))
        completed = sum((item.completed_quantity for item in orders), Decimal('0'))
        return ProductionDashboard(
            total_orders=len(orders),
            draft_orders=sum(item.status == WorkOrderStatus.DRAFT for item in orders),
            released_orders=sum(item.status == WorkOrderStatus.RELEASED for item in orders),
            in_progress_orders=sum(item.status == WorkOrderStatus.IN_PROGRESS for item in orders),
            completed_orders=sum(item.status == WorkOrderStatus.COMPLETED for item in orders),
            planned_quantity=planned, completed_quantity=completed,
            completion_rate=(completed / planned * Decimal('100')) if planned else Decimal('0'),
        )

    @staticmethod
    async def create_order(db: AsyncSession, obj: CreateWorkOrder) -> WorkOrderDetail:
        product = await db.scalar(select(Material).where(Material.id == obj.product_material_id, Material.deleted == 0))
        if not product or not product.producible:
            raise errors.ConflictError(msg='PRODUCT_NOT_PRODUCIBLE')
        bom = await db.scalar(select(Bom).where(Bom.id == obj.bom_id, Bom.deleted == 0))
        if not bom or bom.status != BomStatus.ACTIVE or bom.product_material_id != product.id:
            raise errors.ConflictError(msg='BOM_NOT_ACTIVE_FOR_PRODUCT')
        routing = await db.scalar(select(Routing).where(Routing.id == obj.routing_id, Routing.deleted == 0))
        if not routing or routing.status != RoutingStatus.ACTIVE or routing.product_material_id != product.id:
            raise errors.ConflictError(msg='ROUTING_NOT_ACTIVE_FOR_PRODUCT')
        number = (obj.work_order_no or f'WO-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await production_repo.get_order_by_no(db, number):
            raise errors.ConflictError(msg='WORK_ORDER_NO_EXISTS')
        order = WorkOrder(
            work_order_no=number, product_material_id=product.id, bom_id=bom.id, routing_id=routing.id,
            planned_quantity=obj.planned_quantity, product_code_snapshot=product.material_code,
            product_name_snapshot=product.material_name, bom_code_snapshot=bom.bom_code,
            bom_version_snapshot=bom.bom_version, routing_code_snapshot=routing.routing_code,
            routing_version_snapshot=routing.routing_version, planned_start_at=obj.planned_start_at,
            planned_end_at=obj.planned_end_at, remark=obj.remark,
        )
        db.add(order)
        await db.flush()
        routing_rows = (await db.scalars(select(RoutingOperation).where(RoutingOperation.routing_id == routing.id, RoutingOperation.deleted == 0).order_by(RoutingOperation.sequence_no))).all()
        operations: list[WorkOrderOperation] = []
        operation_by_routing_row: dict[int, WorkOrderOperation] = {}
        for row in routing_rows:
            operation = await db.scalar(select(Operation).where(Operation.id == row.operation_id, Operation.deleted == 0))
            if not operation:
                raise errors.ConflictError(msg='ROUTING_OPERATION_NOT_FOUND')
            snapshot = WorkOrderOperation(
                work_order_id=order.id, sequence_no=row.sequence_no, operation_id=operation.id,
                operation_code_snapshot=operation.operation_code,
                operation_name_snapshot=row.operation_name_override or row.operation_name_snapshot or operation.operation_name,
                work_center_id=row.work_center_id,
            )
            db.add(snapshot)
            operations.append(snapshot)
            operation_by_routing_row[row.id] = snapshot
        bom_rows = (await db.scalars(select(BomItem).where(BomItem.bom_id == bom.id, BomItem.deleted == 0).order_by(BomItem.line_no))).all()
        requirements: list[WorkOrderMaterialRequirement] = []
        requirement_by_bom_item: dict[int, WorkOrderMaterialRequirement] = {}
        for row in bom_rows:
            material = await db.scalar(select(Material).where(Material.id == row.component_material_id, Material.deleted == 0))
            if not material:
                raise errors.ConflictError(msg='BOM_COMPONENT_NOT_FOUND')
            base_required = row.quantity * obj.planned_quantity / bom.base_quantity
            required = base_required * (Decimal('1') + row.loss_rate / Decimal('100')) + row.fixed_loss_qty
            snapshot = WorkOrderMaterialRequirement(
                work_order_id=order.id, line_no=row.line_no, bom_item_id=row.id,
                material_id=material.id, unit_id=row.unit_id, required_quantity=required,
                material_code_snapshot=material.material_code, material_name_snapshot=material.material_name,
            )
            db.add(snapshot)
            requirements.append(snapshot)
            requirement_by_bom_item[row.id] = snapshot
        await db.flush()
        allocations: list[WorkOrderMaterialAllocation] = []
        allocation_plan = await db.scalar(
            select(OperationMaterialPlan).where(
                OperationMaterialPlan.bom_id == bom.id,
                OperationMaterialPlan.routing_id == routing.id,
                OperationMaterialPlan.status == OperationMaterialPlanStatus.ACTIVE,
                OperationMaterialPlan.deleted == 0,
            )
        )
        if allocation_plan:
            plan_rows = (await db.scalars(
                select(OperationMaterialRequirement).where(
                    OperationMaterialRequirement.plan_id == allocation_plan.id,
                    OperationMaterialRequirement.deleted == 0,
                )
            )).all()
            totals: dict[int, Decimal] = {}
            counts: dict[int, int] = {}
            for item in plan_rows:
                totals[item.bom_item_id] = totals.get(item.bom_item_id, Decimal('0')) + item.quantity
                counts[item.bom_item_id] = counts.get(item.bom_item_id, 0) + 1
            for item in plan_rows:
                requirement = requirement_by_bom_item.get(item.bom_item_id)
                operation_snapshot = operation_by_routing_row.get(item.routing_operation_id)
                if not requirement or not operation_snapshot or totals[item.bom_item_id] <= 0:
                    raise errors.ConflictError(msg='ACTIVE_OPERATION_MATERIAL_PLAN_INVALID')
                allocation = WorkOrderMaterialAllocation(
                    work_order_id=order.id,
                    requirement_id=requirement.id,
                    work_order_operation_id=operation_snapshot.id,
                    planned_quantity=requirement.required_quantity * item.quantity / totals[item.bom_item_id],
                )
                db.add(allocation)
                allocations.append(allocation)
                if counts[item.bom_item_id] == 1:
                    requirement.work_order_operation_id = operation_snapshot.id
            await db.flush()
        return ProductionService._detail(order, operations, requirements, allocations)

    @staticmethod
    async def release_order(db: AsyncSession, order_id: int) -> WorkOrderDetail:
        order = await production_repo.get_order(db, order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        if order.status == WorkOrderStatus.RELEASED:
            return await ProductionService.get_order(db, order.id)
        if order.status != WorkOrderStatus.DRAFT:
            raise errors.ConflictError(msg='WORK_ORDER_NOT_DRAFT')
        if not await production_repo.operations(db, order.id) or not await production_repo.requirements(db, order.id):
            raise errors.ConflictError(msg='WORK_ORDER_SNAPSHOT_INCOMPLETE')
        order.status = WorkOrderStatus.RELEASED
        await db.flush()
        return await ProductionService.get_order(db, order.id)

    @staticmethod
    async def start_order(db: AsyncSession, order_id: int) -> WorkOrderDetail:
        order = await production_repo.get_order(db, order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        if order.status == WorkOrderStatus.IN_PROGRESS:
            return await ProductionService.get_order(db, order.id)
        if order.status != WorkOrderStatus.RELEASED:
            raise errors.ConflictError(msg='WORK_ORDER_NOT_RELEASED')
        order.status = WorkOrderStatus.IN_PROGRESS
        order.started_at = timezone.now()
        await db.flush()
        return await ProductionService.get_order(db, order.id)

    @staticmethod
    async def issue_material(db: AsyncSession, obj: CreateMaterialIssue) -> MaterialIssueDetail:
        order = await production_repo.get_order(db, obj.work_order_id, lock=True)
        if not order or order.status not in (WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS):
            raise errors.ConflictError(msg='WORK_ORDER_NOT_ISSUABLE')
        number = (obj.issue_no or f'ISS-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        issue = MaterialIssue(issue_no=number, work_order_id=order.id, remark=obj.remark)
        db.add(issue)
        await db.flush()
        lines: list[MaterialIssueLine] = []
        for index, item in enumerate(obj.lines, start=1):
            requirement = await production_repo.requirement(db, item.requirement_id, lock=True)
            if not requirement or requirement.work_order_id != order.id:
                raise errors.NotFoundError(msg='WORK_ORDER_REQUIREMENT_NOT_FOUND')
            if requirement.issued_quantity + item.quantity > requirement.required_quantity:
                raise errors.ConflictError(msg='ISSUE_QUANTITY_EXCEEDS_REQUIREMENT')
            transaction = await inventory_service.post_transaction(
                db, idempotency_key=f'MATERIAL_ISSUE:{issue.id}:{index}', transaction_type=StockTransactionType.ISSUE,
                material_id=requirement.material_id, lot_id=item.lot_id, warehouse_id=item.warehouse_id,
                location_id=item.location_id, quantity_delta=-item.quantity, reference_type='MATERIAL_ISSUE',
                reference_id=issue.id, reference_no=issue.issue_no, remark=obj.remark,
                operator_id=ProductionService._operator_id(),
            )
            line = MaterialIssueLine(
                issue_id=issue.id, requirement_id=requirement.id, material_id=requirement.material_id,
                lot_id=item.lot_id, warehouse_id=item.warehouse_id, location_id=item.location_id,
                quantity=item.quantity, stock_transaction_id=transaction.id,
            )
            db.add(line)
            lines.append(line)
            requirement.issued_quantity += item.quantity
        await db.flush()
        detail = MaterialIssueDetail.model_validate(issue)
        detail.lines = [MaterialIssueLineDetail.model_validate(line) for line in lines]
        return detail

    @staticmethod
    async def list_issues(db: AsyncSession, order_id: int) -> list[MaterialIssueDetail]:
        if not await production_repo.get_order(db, order_id):
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        result = []
        for issue in await production_repo.issues(db, order_id):
            detail = MaterialIssueDetail.model_validate(issue)
            detail.lines = [MaterialIssueLineDetail.model_validate(line) for line in await production_repo.issue_lines(db, issue.id)]
            result.append(detail)
        return result

    @staticmethod
    async def return_material(db: AsyncSession, obj: CreateMaterialReturn) -> MaterialReturn:
        order = await production_repo.get_order(db, obj.work_order_id, lock=True)
        if not order or order.status not in (WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS):
            raise errors.ConflictError(msg='WORK_ORDER_NOT_RETURNABLE')
        number = (obj.return_no or f'RET-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        document = MaterialReturn(return_no=number, work_order_id=order.id, remark=obj.remark)
        db.add(document)
        await db.flush()
        for index, item in enumerate(obj.lines, start=1):
            issue_line = await production_repo.issue_line(db, item.issue_line_id, lock=True)
            if not issue_line:
                raise errors.NotFoundError(msg='MATERIAL_ISSUE_LINE_NOT_FOUND')
            requirement = await production_repo.requirement(db, issue_line.requirement_id, lock=True)
            if not requirement or requirement.work_order_id != order.id:
                raise errors.ConflictError(msg='ISSUE_LINE_WORK_ORDER_MISMATCH')
            if issue_line.returned_quantity + item.quantity > issue_line.quantity:
                raise errors.ConflictError(msg='RETURN_QUANTITY_EXCEEDS_ISSUED')
            transaction = await inventory_service.post_transaction(
                db, idempotency_key=f'MATERIAL_RETURN:{document.id}:{index}', transaction_type=StockTransactionType.RETURN,
                material_id=issue_line.material_id, lot_id=issue_line.lot_id, warehouse_id=issue_line.warehouse_id,
                location_id=issue_line.location_id, quantity_delta=item.quantity, reference_type='MATERIAL_RETURN',
                reference_id=document.id, reference_no=document.return_no, remark=obj.remark,
                operator_id=ProductionService._operator_id(),
            )
            db.add(MaterialReturnLine(return_id=document.id, issue_line_id=issue_line.id, quantity=item.quantity, stock_transaction_id=transaction.id))
            issue_line.returned_quantity += item.quantity
            requirement.returned_quantity += item.quantity
        await db.flush()
        return document

    @staticmethod
    async def report_completion(db: AsyncSession, obj: CreateProductionReport) -> ProductionReport:
        order = await production_repo.get_order(db, obj.work_order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        requested_number = obj.report_no.strip().upper() if obj.report_no else None
        idempotency_key = obj.idempotency_key.strip() if obj.idempotency_key else None
        if obj.idempotency_key is not None and not idempotency_key:
            raise errors.RequestError(msg='PRODUCTION_REPORT_IDEMPOTENCY_KEY_REQUIRED')
        existing_by_key = None
        if idempotency_key:
            existing_by_key = await db.scalar(
                select(ProductionReport).where(
                    ProductionReport.work_order_id == order.id,
                    ProductionReport.idempotency_key == idempotency_key,
                    ProductionReport.deleted == 0,
                ).with_for_update()
            )
        existing_by_number = None
        if requested_number:
            existing_by_number = await db.scalar(
                select(ProductionReport).where(
                    ProductionReport.report_no == requested_number,
                    ProductionReport.deleted == 0,
                ).with_for_update()
            )
        if existing_by_key and existing_by_number and existing_by_key.id != existing_by_number.id:
            raise errors.ConflictError(msg='PRODUCTION_REPORT_IDEMPOTENCY_CONFLICT')
        existing = existing_by_key or existing_by_number
        if existing:
            requested_lot_id = obj.lot_id
            if obj.lot_no:
                requested_lot = await db.scalar(
                    select(MaterialLot).where(
                        MaterialLot.lot_no == obj.lot_no.strip().upper(),
                        MaterialLot.deleted == 0,
                    )
                )
                requested_lot_id = requested_lot.id if requested_lot else None
            same_request = (
                existing.work_order_id == obj.work_order_id
                and existing.good_quantity == obj.good_quantity
                and existing.scrap_quantity == obj.scrap_quantity
                and existing.warehouse_id == obj.warehouse_id
                and existing.location_id == obj.location_id
                and existing.lot_id == requested_lot_id
                and (not requested_number or existing.report_no == requested_number)
                and (not idempotency_key or existing.idempotency_key == idempotency_key)
            )
            if not same_request:
                raise errors.ConflictError(msg='PRODUCTION_REPORT_IDEMPOTENCY_CONFLICT')
            return existing
        if order.status != WorkOrderStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='WORK_ORDER_NOT_IN_PROGRESS')
        if order.completed_quantity + obj.good_quantity > order.planned_quantity:
            raise errors.ConflictError(msg='COMPLETION_EXCEEDS_PLANNED_QUANTITY')
        number = requested_number or f'RPT-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper()
        lot: MaterialLot | None = None
        if obj.lot_id:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == obj.lot_id, MaterialLot.deleted == 0))
            if not lot or lot.material_id != order.product_material_id:
                raise errors.ConflictError(msg='OUTPUT_LOT_MATERIAL_MISMATCH')
        elif obj.lot_no:
            lot_no = obj.lot_no.strip().upper()
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == lot_no, MaterialLot.deleted == 0))
            if lot and lot.material_id != order.product_material_id:
                raise errors.ConflictError(msg='OUTPUT_LOT_MATERIAL_MISMATCH')
            if not lot:
                product = await db.scalar(select(Material).where(Material.id == order.product_material_id, Material.deleted == 0))
                lot = MaterialLot(
                    lot_no=lot_no, material_id=order.product_material_id, lot_type=LotType.FINISHED,
                    source_type=LotSourceType.WORK_ORDER, source_ref_id=order.id, source_ref_no=order.work_order_no,
                    quantity=obj.good_quantity, unit_id=product.base_unit_id if product else None,
                    quality_status=QualityStatus.UNINSPECTED if product and product.quality_inspection_required else QualityStatus.PASS,
                )
                db.add(lot)
                await db.flush()
        else:
            product = await db.scalar(select(Material).where(Material.id == order.product_material_id, Material.deleted == 0))
            if product and product.batch_control:
                raise errors.RequestError(msg='OUTPUT_LOT_REQUIRED')
        transaction = await inventory_service.post_transaction(
            db, idempotency_key=f'PRODUCTION_REPORT:{order.id}:{idempotency_key or number}', transaction_type=StockTransactionType.PRODUCTION_RECEIPT,
            material_id=order.product_material_id, lot_id=lot.id if lot else None,
            warehouse_id=obj.warehouse_id, location_id=obj.location_id, quantity_delta=obj.good_quantity,
            reference_type='PRODUCTION_REPORT', reference_id=order.id, reference_no=number,
            remark=obj.remark, operator_id=ProductionService._operator_id(),
        )
        report = ProductionReport(
            report_no=number, work_order_id=order.id, good_quantity=obj.good_quantity,
            scrap_quantity=obj.scrap_quantity, warehouse_id=obj.warehouse_id, location_id=obj.location_id,
            lot_id=lot.id if lot else None, stock_transaction_id=transaction.id,
            idempotency_key=idempotency_key, remark=obj.remark,
        )
        db.add(report)
        order.completed_quantity += obj.good_quantity
        order.scrap_quantity += obj.scrap_quantity
        if order.completed_quantity >= order.planned_quantity:
            order.status = WorkOrderStatus.COMPLETED
            order.completed_at = timezone.now()
        await db.flush()
        # Keep the quality dependency local: a finished lot gets a pending final
        # inspection only when an active FINAL template exists for the product.
        if lot is not None:
            from backend.plugin.quality.service import quality_service

            await quality_service.create_final_inspection(
                db,
                material_id=order.product_material_id,
                lot=lot,
                source_id=report.id,
                source_no=report.report_no,
                quantity=obj.good_quantity,
            )
        return report


production_service = ProductionService()
