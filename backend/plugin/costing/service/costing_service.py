from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import sqlalchemy as sa
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.costing.enums import CostElement, CostPeriodStatus, CostPostingStatus, MarginDimension
from backend.plugin.costing.model import CostPeriod, MaterialCost, WorkOrderCost, WorkOrderCostLine
from backend.plugin.costing.schema.costing import CostPeriodCreate, MarginDashboard, MarginRow, WorkOrderCostDetail
from backend.plugin.production.model import MaterialIssue, MaterialIssueLine, ProductionExecution, WorkOrder
from backend.plugin.production.model.execution import MaterialConsumption
from backend.plugin.purchasing.model import PurchaseOrderLine, SupplierReceipt, SupplierReceiptLine
from backend.plugin.sales.model import SalesOrderLine, Shipment, ShipmentLine
from backend.utils.timezone import timezone


MONEY = Decimal('0.000001')


def money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY, rounding=ROUND_HALF_UP)


class CostingService:
    @staticmethod
    async def create_period(db: AsyncSession, obj: CostPeriodCreate) -> CostPeriod:
        duplicate = await db.scalar(select(CostPeriod).where(CostPeriod.period_code == obj.period_code, CostPeriod.deleted == 0))
        if duplicate:
            raise errors.RequestError(msg='COST_PERIOD_ALREADY_EXISTS')
        period = CostPeriod(**obj.model_dump())
        db.add(period)
        await db.flush()
        return period

    @staticmethod
    async def periods(db: AsyncSession) -> list[CostPeriod]:
        return list((await db.scalars(select(CostPeriod).where(CostPeriod.deleted == 0).order_by(CostPeriod.start_date.desc()))).all())

    @staticmethod
    async def _period(db: AsyncSession, period_id: int) -> CostPeriod:
        period = await db.scalar(select(CostPeriod).where(CostPeriod.id == period_id, CostPeriod.deleted == 0))
        if not period:
            raise errors.NotFoundError(msg='COST_PERIOD_NOT_FOUND')
        return period

    @staticmethod
    async def _material_rates(db: AsyncSession, period: CostPeriod) -> dict[int, Decimal]:
        rows = (await db.execute(
            select(SupplierReceiptLine.material_id, SupplierReceiptLine.quantity, PurchaseOrderLine.unit_price)
            .join(SupplierReceipt, SupplierReceipt.id == SupplierReceiptLine.supplier_receipt_id)
            .join(PurchaseOrderLine, PurchaseOrderLine.id == SupplierReceiptLine.purchase_order_line_id)
            .where(
                SupplierReceiptLine.deleted == 0,
                SupplierReceipt.deleted == 0,
                PurchaseOrderLine.deleted == 0,
                func.date(SupplierReceipt.created_time) >= period.start_date,
                func.date(SupplierReceipt.created_time) <= period.end_date,
                SupplierReceiptLine.quantity > 0,
                PurchaseOrderLine.unit_price.is_not(None),
            )
        )).all()
        totals: dict[int, list[Decimal]] = defaultdict(lambda: [Decimal('0'), Decimal('0')])
        for material_id, quantity, unit_price in rows:
            quantity = money(quantity)
            totals[material_id][0] += quantity
            totals[material_id][1] += quantity * money(unit_price)
        result = {material_id: money(amount / quantity) for material_id, (quantity, amount) in totals.items() if quantity > 0}
        for row in (await db.scalars(select(MaterialCost).where(MaterialCost.period_id == period.id, MaterialCost.deleted == 0))).all():
            result.setdefault(row.material_id, money(row.unit_cost))
        return result

    @staticmethod
    async def calculate_work_order(db: AsyncSession, work_order_id: int, period_id: int, *, post: bool = False) -> WorkOrderCostDetail:
        period = await CostingService._period(db, period_id)
        if period.status == CostPeriodStatus.CLOSED:
            raise errors.RequestError(msg='COST_PERIOD_CLOSED')
        work_order = await db.scalar(select(WorkOrder).where(WorkOrder.id == work_order_id, WorkOrder.deleted == 0))
        if not work_order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        existing = await db.scalar(select(WorkOrderCost).where(WorkOrderCost.period_id == period_id, WorkOrderCost.work_order_id == work_order_id, WorkOrderCost.deleted == 0))
        if existing and existing.status == CostPostingStatus.POSTED:
            return await CostingService.detail(db, existing.id)
        if existing:
            existing.deleted = 1
            existing.deleted_time = timezone.now()
            await db.flush()

        rates = await CostingService._material_rates(db, period)
        consumptions = list((await db.scalars(
            select(MaterialConsumption).join(ProductionExecution, ProductionExecution.id == MaterialConsumption.execution_id)
            .where(MaterialConsumption.deleted == 0, ProductionExecution.work_order_id == work_order_id, ProductionExecution.deleted == 0)
        )).all())
        material_total = Decimal('0')
        material_facts: list[tuple[int, int, Decimal, Decimal, Decimal, str]] = []
        for row in consumptions:
            rate = rates.get(row.material_id, Decimal('0'))
            amount = money(row.quantity) * rate
            material_total += amount
            material_facts.append((row.id, row.material_id, row.quantity, rate, amount, f'Material consumption {row.consumption_no}'))
        if not material_facts:
            issue_lines = list((await db.scalars(
                select(MaterialIssueLine).join(MaterialIssue, MaterialIssue.id == MaterialIssueLine.issue_id).where(
                    MaterialIssueLine.deleted == 0, MaterialIssue.deleted == 0, MaterialIssue.work_order_id == work_order_id,
                )
            )).all())
            for row in issue_lines:
                rate = rates.get(row.material_id, Decimal('0')); amount = money(row.quantity - row.returned_quantity) * rate
                material_total += amount
                material_facts.append((row.id, row.material_id, row.quantity - row.returned_quantity, rate, amount, 'Material issue line'))
        executions = list((await db.scalars(select(ProductionExecution).where(ProductionExecution.work_order_id == work_order_id, ProductionExecution.deleted == 0))).all())
        hours = Decimal('0')
        for execution in executions:
            if execution.completed_at and execution.started_at:
                hours += Decimal(str((execution.completed_at - execution.started_at).total_seconds())) / Decimal('3600')
        hours = money(hours)
        labor = money(hours * money(period.labor_rate_per_hour))
        machine = money(hours * money(period.machine_rate_per_hour))
        overhead = money(hours * money(period.overhead_rate_per_hour))
        good = money(work_order.completed_quantity)
        scrap = money(work_order.scrap_quantity)
        quality_loss = money((material_total / max(good + scrap, Decimal('1'))) * scrap)
        total = money(material_total + labor + machine + overhead + quality_loss)
        status = CostPostingStatus.POSTED if post else CostPostingStatus.CALCULATED
        now = timezone.now()
        cost = WorkOrderCost(
            period_id=period_id, work_order_id=work_order.id, work_order_no_snapshot=work_order.work_order_no,
            product_material_id=work_order.product_material_id, product_code_snapshot=work_order.product_code_snapshot,
            product_name_snapshot=work_order.product_name_snapshot, good_quantity=good, scrap_quantity=scrap,
            material_cost=money(material_total), labor_cost=labor, machine_cost=machine, overhead_cost=overhead,
            quality_loss_cost=quality_loss, total_cost=total, unit_cost=money(total / good) if good > 0 else Decimal('0'),
            status=status, calculated_at=now, posted_at=now if post else None,
        )
        db.add(cost)
        await db.flush()
        for source_id, material_id, quantity, rate, amount, description in material_facts:
            db.add(WorkOrderCostLine(work_order_cost_id=cost.id, element=CostElement.MATERIAL, source_type='MATERIAL_CONSUMPTION', source_id=source_id, material_id=material_id, description=description, quantity=quantity, unit_rate=rate, amount=amount))
        if hours > 0:
            for element, rate, amount in ((CostElement.LABOR, period.labor_rate_per_hour, labor), (CostElement.MACHINE, period.machine_rate_per_hour, machine), (CostElement.OVERHEAD, period.overhead_rate_per_hour, overhead)):
                db.add(WorkOrderCostLine(work_order_cost_id=cost.id, element=element, source_type='PRODUCTION_EXECUTION', description='Execution time allocation', quantity=hours, unit_rate=rate, amount=amount))
        if quality_loss > 0:
            db.add(WorkOrderCostLine(work_order_cost_id=cost.id, element=CostElement.QUALITY_LOSS, source_type='SCRAP', description='Scrap quality loss allocation', quantity=scrap, unit_rate=money(quality_loss / scrap) if scrap else Decimal('0'), amount=quality_loss))
        await db.flush()
        return await CostingService.detail(db, cost.id)

    @staticmethod
    async def detail(db: AsyncSession, cost_id: int) -> WorkOrderCostDetail:
        cost = await db.scalar(select(WorkOrderCost).where(WorkOrderCost.id == cost_id, WorkOrderCost.deleted == 0))
        if not cost:
            raise errors.NotFoundError(msg='WORK_ORDER_COST_NOT_FOUND')
        lines = list((await db.scalars(select(WorkOrderCostLine).where(WorkOrderCostLine.work_order_cost_id == cost.id, WorkOrderCostLine.deleted == 0).order_by(WorkOrderCostLine.id))).all())
        return WorkOrderCostDetail.model_validate({**{key: getattr(cost, key) for key in ('id', 'period_id', 'work_order_id', 'work_order_no_snapshot', 'product_material_id', 'product_code_snapshot', 'product_name_snapshot', 'good_quantity', 'scrap_quantity', 'material_cost', 'labor_cost', 'machine_cost', 'overhead_cost', 'quality_loss_cost', 'total_cost', 'unit_cost', 'status', 'calculated_at', 'posted_at')}, 'lines': lines})

    @staticmethod
    async def work_order_cost(db: AsyncSession, work_order_id: int, period_id: int) -> WorkOrderCostDetail:
        cost = await db.scalar(select(WorkOrderCost).where(WorkOrderCost.period_id == period_id, WorkOrderCost.work_order_id == work_order_id, WorkOrderCost.deleted == 0))
        if not cost:
            raise errors.NotFoundError(msg='WORK_ORDER_COST_NOT_CALCULATED')
        return await CostingService.detail(db, cost.id)

    @staticmethod
    async def post_work_order(db: AsyncSession, work_order_id: int, period_id: int) -> WorkOrderCostDetail:
        cost = await db.scalar(select(WorkOrderCost).where(WorkOrderCost.period_id == period_id, WorkOrderCost.work_order_id == work_order_id, WorkOrderCost.deleted == 0))
        if cost and cost.status == CostPostingStatus.POSTED:
            return await CostingService.detail(db, cost.id)
        if not cost:
            return await CostingService.calculate_work_order(db, work_order_id, period_id, post=True)
        cost.status = CostPostingStatus.POSTED
        cost.posted_at = timezone.now()
        await db.flush()
        return await CostingService.detail(db, cost.id)

    @staticmethod
    async def close_period(db: AsyncSession, period_id: int) -> CostPeriod:
        period = await CostingService._period(db, period_id)
        pending = await db.scalar(select(func.count(WorkOrderCost.id)).where(WorkOrderCost.period_id == period_id, WorkOrderCost.deleted == 0, WorkOrderCost.status != CostPostingStatus.POSTED))
        if pending:
            raise errors.RequestError(msg='COST_PERIOD_HAS_UNPOSTED_WORK_ORDERS')
        period.status = CostPeriodStatus.CLOSED
        period.closed_at = timezone.now()
        await db.flush()
        return period

    @staticmethod
    async def margin(db: AsyncSession, period_id: int | None, dimension: MarginDimension) -> MarginDashboard:
        period = await CostingService._period(db, period_id) if period_id else None
        filters = [ShipmentLine.deleted == 0, Shipment.deleted == 0, SalesOrderLine.deleted == 0]
        if period:
            filters.extend([func.date(Shipment.created_time) >= period.start_date, func.date(Shipment.created_time) <= period.end_date])
        rows = (await db.execute(select(ShipmentLine, Shipment, SalesOrderLine).join(Shipment, Shipment.id == ShipmentLine.shipment_id).join(SalesOrderLine, SalesOrderLine.id == ShipmentLine.sales_order_line_id).where(*filters))).all()
        costs = list((await db.scalars(select(WorkOrderCost).where(WorkOrderCost.deleted == 0, WorkOrderCost.status == CostPostingStatus.POSTED, *( [WorkOrderCost.period_id == period_id] if period else [] )))).all())
        weighted: dict[int, tuple[Decimal, Decimal]] = defaultdict(lambda: [Decimal('0'), Decimal('0')])
        for cost in costs:
            weighted[cost.product_material_id][0] += money(cost.good_quantity)
            weighted[cost.product_material_id][1] += money(cost.total_cost)
        grouped: dict[str, dict[str, Decimal | str]] = {}
        for line, shipment, order_line in rows:
            key = str(line.material_id) if dimension == MarginDimension.PRODUCT else str(shipment.customer_id)
            name = line.material_id and (order_line.material_name_snapshot if dimension == MarginDimension.PRODUCT else shipment.customer_name_snapshot) or key
            quantity = money(line.quantity)
            revenue = money(quantity * money(order_line.unit_price))
            qty, amount = weighted.get(line.material_id, (Decimal('0'), Decimal('0')))
            unit_cost = money(amount / qty) if qty > 0 else Decimal('0')
            bucket = grouped.setdefault(key, {'name': str(name), 'shipped_quantity': Decimal('0'), 'revenue': Decimal('0'), 'cogs': Decimal('0'), 'covered': Decimal('0')})
            bucket['shipped_quantity'] += quantity; bucket['revenue'] += revenue; bucket['cogs'] += quantity * unit_cost; bucket['covered'] += quantity if qty > 0 else Decimal('0')
        result: list[MarginRow] = []
        for key, bucket in grouped.items():
            revenue = money(bucket['revenue']); cogs = money(bucket['cogs']); profit = money(revenue - cogs)
            shipped = money(bucket['shipped_quantity'])
            result.append(MarginRow(dimension=dimension, key=key, name=str(bucket['name']), shipped_quantity=shipped, revenue=revenue, cogs=cogs, gross_profit=profit, margin_rate=money(profit / revenue * 100) if revenue else Decimal('0'), cost_coverage=money(bucket['covered'] / shipped * 100) if shipped else Decimal('0')))
        revenue = money(sum((row.revenue for row in result), Decimal('0'))); cogs = money(sum((row.cogs for row in result), Decimal('0'))); profit = money(revenue - cogs)
        return MarginDashboard(period_id=period.id if period else None, period_code=period.period_code if period else None, dimension=dimension, rows=result, revenue=revenue, cogs=cogs, gross_profit=profit, margin_rate=money(profit / revenue * 100) if revenue else Decimal('0'))


costing_service = CostingService()
