from collections import Counter
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.sales.enums import DeliveryPerformanceStatus, SalesOrderStatus, ShipmentStatus
from backend.plugin.sales.model import (
    SalesOrder,
    SalesOrderDeliveryPerformance,
    SalesOrderLine,
    Shipment,
    ShipmentLine,
    SalesOrderPromiseAssessment,
)
from backend.plugin.sales.schema.sales import (
    DeliveryDashboard,
    DeliveryPerformanceDetail,
    DeliveryRecalculateResult,
)
from backend.plugin.sales.service.sales_service import SalesService
from backend.utils.timezone import timezone

ZERO = Decimal('0')


class DeliveryService:
    @staticmethod
    async def refresh_order(db: AsyncSession, order_id: int) -> list[DeliveryPerformanceDetail]:
        order = await SalesService.get_order_model(db, order_id)
        lines = await SalesService.order_lines(db, order.id)
        assessed_at = timezone.now()
        result: list[DeliveryPerformanceDetail] = []
        for line in lines:
            promise = await db.scalar(
                select(SalesOrderPromiseAssessment)
                .where(
                    SalesOrderPromiseAssessment.sales_order_line_id == line.id,
                    SalesOrderPromiseAssessment.deleted == 0,
                )
                .order_by(SalesOrderPromiseAssessment.assessed_at.desc())
            )
            promised = (
                promise.promised_delivery_at
                if promise and promise.promised_delivery_at
                else order.requested_delivery_at or order.created_time + timedelta(days=7)
            )
            shipments = (
                await db.scalars(
                    select(Shipment)
                    .join(ShipmentLine, ShipmentLine.shipment_id == Shipment.id)
                    .where(
                        ShipmentLine.sales_order_line_id == line.id,
                        ShipmentLine.deleted == 0,
                        Shipment.deleted == 0,
                    )
                    .order_by(Shipment.created_time.desc(), Shipment.id.desc())
                )
            ).all()
            delivered = [item for item in shipments if item.status == ShipmentStatus.DELIVERED and item.delivered_at]
            shipped = line.shipped_quantity or ZERO
            in_full = shipped >= line.ordered_quantity
            actual = max((item.delivered_at for item in delivered), default=None) if in_full and len(delivered) == len(shipments) else None
            on_time = actual is not None and actual <= promised
            now = assessed_at
            if actual is not None:
                status = DeliveryPerformanceStatus.OTIF if on_time else DeliveryPerformanceStatus.LATE
            elif in_full:
                status = DeliveryPerformanceStatus.IN_TRANSIT
            elif now > promised:
                status = DeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL
            else:
                status = DeliveryPerformanceStatus.OPEN
            reason = None
            if status in (DeliveryPerformanceStatus.LATE, DeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL):
                risk = promise.risk_status if promise else None
                reason = (
                    'SHORTAGE' if risk == 'SHORTAGE'
                    else 'CAPACITY_RISK' if risk == 'CAPACITY_RISK'
                    else 'EXECUTION'
                )
            last_shipment = shipments[0] if shipments else None
            performance = await db.scalar(
                select(SalesOrderDeliveryPerformance)
                .where(
                    SalesOrderDeliveryPerformance.sales_order_line_id == line.id,
                    SalesOrderDeliveryPerformance.deleted == 0,
                )
                .with_for_update()
            )
            values = dict(
                sales_order_id=order.id,
                sales_order_line_id=line.id,
                material_id=line.material_id,
                promised_delivery_at=promised,
                actual_delivery_at=actual,
                assessed_at=assessed_at,
                ordered_quantity=line.ordered_quantity,
                shipped_quantity=shipped,
                on_time=on_time,
                in_full=in_full,
                otif_status=status,
                delay_reason=reason,
                last_shipment_id=last_shipment.id if last_shipment else None,
            )
            if performance:
                for key, value in values.items():
                    setattr(performance, key, value)
            else:
                performance = SalesOrderDeliveryPerformance(**values)
                db.add(performance)
            await db.flush()
            result.append(DeliveryPerformanceDetail.model_validate(performance))
        return result

    @staticmethod
    async def list_order_performance(db: AsyncSession, order_id: int) -> list[DeliveryPerformanceDetail]:
        await SalesService.get_order_model(db, order_id)
        rows = (
            await db.scalars(
                select(SalesOrderDeliveryPerformance)
                .where(
                    SalesOrderDeliveryPerformance.sales_order_id == order_id,
                    SalesOrderDeliveryPerformance.deleted == 0,
                )
                .order_by(SalesOrderDeliveryPerformance.sales_order_line_id)
            )
        ).all()
        return [DeliveryPerformanceDetail.model_validate(row) for row in rows]

    @staticmethod
    async def recalculate(db: AsyncSession) -> DeliveryRecalculateResult:
        orders = (
            await db.scalars(
                select(SalesOrder)
                .where(
                    SalesOrder.deleted == 0,
                    SalesOrder.status.in_(
                        [
                            SalesOrderStatus.CONFIRMED,
                            SalesOrderStatus.PARTIALLY_SHIPPED,
                            SalesOrderStatus.SHIPPED,
                        ]
                    ),
                )
                .order_by(SalesOrder.id)
            )
        ).all()
        line_count = 0
        for order in orders:
            line_count += len(await DeliveryService.refresh_order(db, order.id))
        return DeliveryRecalculateResult(
            assessed_order_count=len(orders),
            assessed_line_count=line_count,
            assessed_at=timezone.now(),
        )

    @staticmethod
    async def dashboard(db: AsyncSession) -> DeliveryDashboard:
        rows = (
            await db.scalars(
                select(SalesOrderDeliveryPerformance).where(
                    SalesOrderDeliveryPerformance.deleted == 0
                )
            )
        ).all()
        statuses = {row.otif_status for row in rows}
        orders = {row.sales_order_id for row in rows}
        completed_orders = {
            row.sales_order_id
            for row in rows
            if row.otif_status in (DeliveryPerformanceStatus.OTIF, DeliveryPerformanceStatus.LATE)
        }
        in_transit_orders = {
            row.sales_order_id for row in rows if row.otif_status == DeliveryPerformanceStatus.IN_TRANSIT
        }
        delayed_orders = {
            row.sales_order_id
            for row in rows
            if row.otif_status
            in (
                DeliveryPerformanceStatus.LATE,
                DeliveryPerformanceStatus.LATE_AND_NOT_IN_FULL,
                DeliveryPerformanceStatus.NOT_IN_FULL,
            )
        }
        line_count = len(rows)
        otif_count = sum(row.otif_status == DeliveryPerformanceStatus.OTIF for row in rows)
        on_time_count = sum(row.on_time for row in rows)
        in_full_count = sum(row.in_full for row in rows)
        rate = lambda count: (Decimal(count) / Decimal(line_count) * Decimal('100')).quantize(Decimal('0.01')) if line_count else ZERO
        return DeliveryDashboard(
            order_count=len(orders),
            completed_order_count=len(completed_orders),
            in_transit_order_count=len(in_transit_orders),
            delayed_order_count=len(delayed_orders),
            line_count=line_count,
            otif_line_count=otif_count,
            on_time_line_count=on_time_count,
            in_full_line_count=in_full_count,
            otif_rate=rate(otif_count),
            on_time_rate=rate(on_time_count),
            in_full_rate=rate(in_full_count),
            delay_reasons=dict(Counter(row.delay_reason for row in rows if row.delay_reason)),
        )


delivery_service = DeliveryService()
