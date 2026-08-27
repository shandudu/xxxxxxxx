from collections import Counter
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.inventory.model import InventoryBalance
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import WorkOrder
from backend.plugin.purchasing.enums import PurchaseOrderStatus
from backend.plugin.purchasing.model import PurchaseOrder, PurchaseOrderLine
from backend.plugin.sales.enums import SalesOrderStatus
from backend.plugin.sales.model import SalesOrder, SalesOrderLine, SalesOrderPromiseAssessment
from backend.plugin.sales.service.sales_service import SalesService
from backend.plugin.sales.schema.sales import PromiseAssessmentDetail, PromiseDashboard, PromiseRecalculateResult
from backend.utils.timezone import timezone

ZERO = Decimal('0')


class PromiseService:
    @staticmethod
    async def _supply(db: AsyncSession, material_id: int) -> tuple[Decimal, Decimal, Decimal]:
        balances = (await db.scalars(select(InventoryBalance).where(InventoryBalance.material_id == material_id, InventoryBalance.deleted == 0))).all()
        atp = sum((max((row.quantity or ZERO) - (row.reserved_quantity or ZERO), ZERO) for row in balances), ZERO)
        purchase_rows = (await db.execute(
            select(PurchaseOrderLine.ordered_quantity, PurchaseOrderLine.received_quantity)
            .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.purchase_order_id)
            .where(PurchaseOrderLine.material_id == material_id, PurchaseOrderLine.deleted == 0, PurchaseOrder.deleted == 0, PurchaseOrder.status.in_([PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED]))
        )).all()
        open_purchase = sum((max((ordered or ZERO) - (received or ZERO), ZERO) for ordered, received in purchase_rows), ZERO)
        work_orders = (await db.scalars(select(WorkOrder).where(WorkOrder.product_material_id == material_id, WorkOrder.deleted == 0, WorkOrder.status.in_([WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS])))).all()
        open_production = sum((max((row.planned_quantity or ZERO) - (row.completed_quantity or ZERO), ZERO) for row in work_orders), ZERO)
        return atp, open_purchase, open_production

    @staticmethod
    async def assess_order(db: AsyncSession, order_id: int) -> list[PromiseAssessmentDetail]:
        order = await SalesService.get_order_model(db, order_id)
        lines = await SalesService.order_lines(db, order.id)
        requested = order.requested_delivery_at or (order.created_time + timedelta(days=7))
        assessed_at = timezone.now()
        result: list[PromiseAssessmentDetail] = []
        for line in lines:
            remaining = max(line.ordered_quantity - line.shipped_quantity, ZERO)
            atp, purchase, production = await PromiseService._supply(db, line.material_id)
            ctp = atp + purchase + production
            shortage = max(remaining - ctp, ZERO)
            capacity_shortage = max(remaining - atp - purchase, ZERO)
            if shortage > ZERO:
                risk_status = 'SHORTAGE'
                promised = requested + timedelta(days=7)
                notes = f'缺口 {shortage}，需补充采购或生产'
            elif capacity_shortage > ZERO and requested < assessed_at + timedelta(days=3):
                risk_status = 'CAPACITY_RISK'
                promised = requested + timedelta(days=production > ZERO and 2 or 5)
                notes = f'依赖生产供给 {capacity_shortage}，存在产能交期风险'
            elif atp >= remaining:
                risk_status = 'COMMITTABLE'
                promised = assessed_at
                notes = '现有可用库存满足剩余需求'
            else:
                risk_status = 'COMMITTABLE'
                promised = requested
                notes = '库存与已计划供应可覆盖需求'
            assessment = await db.scalar(select(SalesOrderPromiseAssessment).where(SalesOrderPromiseAssessment.sales_order_line_id == line.id, SalesOrderPromiseAssessment.deleted == 0).with_for_update())
            values = dict(sales_order_id=order.id, sales_order_line_id=line.id, material_id=line.material_id, requested_delivery_at=requested, assessed_at=assessed_at, ordered_quantity=line.ordered_quantity, shipped_quantity=line.shipped_quantity, atp_quantity=atp, open_purchase_quantity=purchase, open_production_quantity=production, ctp_quantity=ctp, shortage_quantity=shortage, capacity_shortage_quantity=capacity_shortage, promised_delivery_at=promised, risk_status=risk_status, risk_notes=notes)
            if assessment:
                for key, value in values.items(): setattr(assessment, key, value)
            else:
                assessment = SalesOrderPromiseAssessment(**values)
                db.add(assessment)
            await db.flush()
            result.append(PromiseAssessmentDetail.model_validate(assessment))
        return result

    @staticmethod
    async def list_assessments(db: AsyncSession, order_id: int) -> list[PromiseAssessmentDetail]:
        await SalesService.get_order_model(db, order_id)
        rows = (await db.scalars(select(SalesOrderPromiseAssessment).where(SalesOrderPromiseAssessment.sales_order_id == order_id, SalesOrderPromiseAssessment.deleted == 0).order_by(SalesOrderPromiseAssessment.sales_order_line_id))).all()
        return [PromiseAssessmentDetail.model_validate(row) for row in rows]

    @staticmethod
    async def recalculate_open_orders(db: AsyncSession) -> PromiseRecalculateResult:
        """Refresh commitment snapshots after MRP or supply changes."""
        orders = (
            await db.scalars(
                select(SalesOrder)
                .where(
                    SalesOrder.deleted == 0,
                    SalesOrder.status.in_([
                        SalesOrderStatus.CONFIRMED,
                        SalesOrderStatus.PARTIALLY_SHIPPED,
                    ]),
                )
                .order_by(SalesOrder.id)
            )
        ).all()
        assessed_lines = 0
        for order in orders:
            assessed_lines += len(await PromiseService.assess_order(db, order.id))
        return PromiseRecalculateResult(
            assessed_order_count=len(orders),
            assessed_line_count=assessed_lines,
            assessed_at=timezone.now(),
        )

    @staticmethod
    async def dashboard(db: AsyncSession) -> PromiseDashboard:
        rows = (await db.scalars(select(SalesOrderPromiseAssessment).where(SalesOrderPromiseAssessment.deleted == 0))).all()
        risk = Counter(row.risk_status for row in rows)
        return PromiseDashboard(risk_counts=dict(risk), order_count=len({row.sales_order_id for row in rows}), delayed_order_count=len({row.sales_order_id for row in rows if row.risk_status in ('SHORTAGE', 'CAPACITY_RISK', 'DELAYED')}), total_shortage_quantity=sum((row.shortage_quantity or ZERO for row in rows), ZERO), total_capacity_shortage_quantity=sum((row.capacity_shortage_quantity or ZERO for row in rows), ZERO))


promise_service = PromiseService()
