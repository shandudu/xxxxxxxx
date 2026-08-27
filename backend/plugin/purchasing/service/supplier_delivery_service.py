from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.planning.enums import MrpRunStatus
from backend.plugin.planning.model import MrpRequirement, MrpRun
from backend.plugin.purchasing.enums import (
    PurchaseDeliveryPerformanceStatus,
    PurchaseDelayReason,
    PurchaseOrderStatus,
)
from backend.plugin.purchasing.model import (
    PurchaseOrder,
    PurchaseOrderDeliveryPerformance,
    PurchaseOrderLine,
    SupplierReceipt,
    SupplierReceiptLine,
)
from backend.plugin.purchasing.schema.purchasing import (
    PurchaseDeliveryDashboard,
    PurchaseDeliveryPerformanceDetail,
    PurchaseDeliveryRecalculateResult,
)
from backend.plugin.sales.model import SalesOrderPromiseAssessment
from backend.utils.timezone import timezone

ZERO = Decimal('0')


class SupplierDeliveryService:
    @staticmethod
    async def _impact(db: AsyncSession, material_id: int) -> tuple[Decimal, int, Decimal]:
        promise_rows = (
            await db.scalars(
                select(SalesOrderPromiseAssessment).where(
                    SalesOrderPromiseAssessment.material_id == material_id,
                    SalesOrderPromiseAssessment.deleted == 0,
                    SalesOrderPromiseAssessment.shortage_quantity > ZERO,
                )
            )
        ).all()
        shortage = sum((row.shortage_quantity or ZERO for row in promise_rows), ZERO)
        order_count = len({row.sales_order_id for row in promise_rows})
        run_id = await db.scalar(
            select(MrpRun.id)
            .where(MrpRun.status == MrpRunStatus.COMPLETED, MrpRun.deleted == 0)
            .order_by(MrpRun.completed_at.desc(), MrpRun.id.desc())
            .limit(1)
        )
        uncovered = ZERO
        if run_id:
            uncovered = await db.scalar(
                select(func.coalesce(func.sum(MrpRequirement.uncovered_quantity), ZERO)).where(
                    MrpRequirement.mrp_run_id == run_id,
                    MrpRequirement.material_id == material_id,
                    MrpRequirement.deleted == 0,
                )
            ) or ZERO
        return shortage, order_count, uncovered

    @staticmethod
    async def refresh_order(
        db: AsyncSession, order_id: int
    ) -> list[PurchaseDeliveryPerformanceDetail]:
        order = await db.scalar(
            select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.deleted == 0)
        )
        if not order:
            return []
        lines = (
            await db.scalars(
                select(PurchaseOrderLine)
                .where(PurchaseOrderLine.purchase_order_id == order.id, PurchaseOrderLine.deleted == 0)
                .order_by(PurchaseOrderLine.line_no)
            )
        ).all()
        assessed_at = timezone.now()
        result: list[PurchaseDeliveryPerformanceDetail] = []
        for line in lines:
            requested = line.requested_delivery_at or order.created_time + timedelta(days=7)
            effective = line.supplier_confirmed_delivery_at or requested
            receipts = (
                await db.scalars(
                    select(SupplierReceipt)
                    .join(SupplierReceiptLine, SupplierReceiptLine.supplier_receipt_id == SupplierReceipt.id)
                    .where(
                        SupplierReceiptLine.purchase_order_line_id == line.id,
                        SupplierReceiptLine.deleted == 0,
                        SupplierReceipt.deleted == 0,
                    )
                    .order_by(SupplierReceipt.created_time.desc(), SupplierReceipt.id.desc())
                )
            ).all()
            received = line.received_quantity or ZERO
            in_full = received >= line.ordered_quantity
            actual = max((receipt.created_time for receipt in receipts), default=None) if in_full else None
            on_time = actual is not None and actual <= effective
            if actual is not None:
                status = (
                    PurchaseDeliveryPerformanceStatus.OTIF
                    if on_time
                    else PurchaseDeliveryPerformanceStatus.LATE
                )
            elif assessed_at > effective:
                status = PurchaseDeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL
            else:
                status = PurchaseDeliveryPerformanceStatus.OPEN
            shortage, impacted_orders, uncovered = await SupplierDeliveryService._impact(
                db, line.material_id
            )
            reason = (
                PurchaseDelayReason.SHORTAGE_IMPACT
                if status in (
                    PurchaseDeliveryPerformanceStatus.LATE,
                    PurchaseDeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL,
                )
                and shortage > ZERO
                else PurchaseDelayReason.SUPPLIER
                if status
                in (
                    PurchaseDeliveryPerformanceStatus.LATE,
                    PurchaseDeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL,
                )
                else None
            )
            delay_end = actual or assessed_at
            days_late = max((delay_end.date() - effective.date()).days, 0) if reason else 0
            performance = await db.scalar(
                select(PurchaseOrderDeliveryPerformance)
                .where(
                    PurchaseOrderDeliveryPerformance.purchase_order_line_id == line.id,
                    PurchaseOrderDeliveryPerformance.deleted == 0,
                )
                .with_for_update()
            )
            values = dict(
                supplier_id=order.supplier_id,
                purchase_order_id=order.id,
                purchase_order_line_id=line.id,
                material_id=line.material_id,
                requested_delivery_at=requested,
                supplier_confirmed_delivery_at=line.supplier_confirmed_delivery_at,
                effective_delivery_at=effective,
                assessed_at=assessed_at,
                ordered_quantity=line.ordered_quantity,
                actual_delivery_at=actual,
                received_quantity=received,
                on_time=on_time,
                in_full=in_full,
                otif_status=status,
                delay_reason=reason,
                days_late=days_late,
                shortage_impact_quantity=shortage,
                impacted_sales_order_count=impacted_orders,
                mrp_uncovered_quantity=uncovered,
            )
            if performance:
                for key, value in values.items():
                    setattr(performance, key, value)
            else:
                performance = PurchaseOrderDeliveryPerformance(**values)
                db.add(performance)
            await db.flush()
            result.append(PurchaseDeliveryPerformanceDetail.model_validate(performance))
        return result

    @staticmethod
    async def list_order_performance(
        db: AsyncSession, order_id: int
    ) -> list[PurchaseDeliveryPerformanceDetail]:
        rows = (
            await db.scalars(
                select(PurchaseOrderDeliveryPerformance)
                .where(
                    PurchaseOrderDeliveryPerformance.purchase_order_id == order_id,
                    PurchaseOrderDeliveryPerformance.deleted == 0,
                )
                .order_by(PurchaseOrderDeliveryPerformance.purchase_order_line_id)
            )
        ).all()
        return [PurchaseDeliveryPerformanceDetail.model_validate(row) for row in rows]

    @staticmethod
    async def recalculate(db: AsyncSession) -> PurchaseDeliveryRecalculateResult:
        orders = (
            await db.scalars(
                select(PurchaseOrder)
                .where(
                    PurchaseOrder.deleted == 0,
                    PurchaseOrder.status.in_(
                        [
                            PurchaseOrderStatus.CONFIRMED,
                            PurchaseOrderStatus.PARTIALLY_RECEIVED,
                            PurchaseOrderStatus.RECEIVED,
                        ]
                    ),
                )
                .order_by(PurchaseOrder.id)
            )
        ).all()
        line_count = 0
        for order in orders:
            line_count += len(await SupplierDeliveryService.refresh_order(db, order.id))
        return PurchaseDeliveryRecalculateResult(
            assessed_order_count=len(orders),
            assessed_line_count=line_count,
            assessed_at=timezone.now(),
        )

    @staticmethod
    async def dashboard(db: AsyncSession) -> PurchaseDeliveryDashboard:
        rows = (
            await db.scalars(
                select(PurchaseOrderDeliveryPerformance).where(
                    PurchaseOrderDeliveryPerformance.deleted == 0
                )
            )
        ).all()
        line_count = len(rows)
        otif_count = sum(
            row.otif_status == PurchaseDeliveryPerformanceStatus.OTIF for row in rows
        )
        delayed = [
            row
            for row in rows
            if row.otif_status
            in (
                PurchaseDeliveryPerformanceStatus.LATE,
                PurchaseDeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL,
            )
        ]
        rates = lambda count: (
            Decimal(count) / Decimal(line_count) * Decimal('100')
        ).quantize(Decimal('0.01')) if line_count else ZERO
        grouped: dict[int, list[PurchaseOrderDeliveryPerformance]] = defaultdict(list)
        for row in rows:
            grouped[row.supplier_id].append(row)
        supplier_otif = [
            {
                'supplier_id': supplier_id,
                'line_count': len(items),
                'otif_line_count': sum(
                    item.otif_status == PurchaseDeliveryPerformanceStatus.OTIF
                    for item in items
                ),
                'otif_rate': float(
                    (
                        Decimal(
                            sum(
                                item.otif_status == PurchaseDeliveryPerformanceStatus.OTIF
                                for item in items
                            )
                        )
                        / Decimal(len(items))
                        * Decimal('100')
                    ).quantize(Decimal('0.01'))
                ) if items else 0.0,
            }
            for supplier_id, items in sorted(grouped.items())
        ]
        return PurchaseDeliveryDashboard(
            order_count=len({row.purchase_order_id for row in rows}),
            supplier_count=len(grouped),
            line_count=line_count,
            otif_line_count=otif_count,
            delayed_line_count=len(delayed),
            otif_rate=rates(otif_count),
            delayed_quantity=sum(
                (max(row.ordered_quantity - row.received_quantity, ZERO) for row in delayed),
                ZERO,
            ),
            shortage_impact_quantity=sum(
                (row.shortage_impact_quantity or ZERO for row in rows), ZERO
            ),
            impacted_sales_order_count=sum(row.impacted_sales_order_count for row in rows),
            supplier_otif=supplier_otif,
        )


supplier_delivery_service = SupplierDeliveryService()
