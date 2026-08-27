from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.schema.monitor_alert import AlertInboxItem, AlertInboxSummary
from backend.plugin.inventory.enums import ReplenishmentAlertLevel, ReplenishmentStatus
from backend.plugin.inventory.model.replenishment import ReplenishmentSuggestion
from backend.plugin.production.enums import AndonStatus
from backend.plugin.production.model.andon import ProductionAndonEvent
from backend.plugin.purchasing.model.purchasing import PurchaseOrderDeliveryPerformance
from backend.plugin.quality.enums import SlaAlertStatus
from backend.plugin.quality.model.quality import QualityWorkItemAlert
from backend.plugin.sales.model.sales import SalesOrderDeliveryPerformance


class AlertService:
    """Build a read-only inbox from the operational alert sources."""

    @staticmethod
    def _priority(severity: str) -> int:
        return {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(severity, 4)

    @staticmethod
    def _item(
        *,
        source: str,
        alert_type: str,
        alert_id: int,
        code: str,
        title: str,
        severity: str,
        status: str,
        due_at: datetime | None,
        owner_id: int | None,
        action_path: str,
        details: dict[str, Any] | None = None,
    ) -> AlertInboxItem:
        return AlertInboxItem(
            source=source,
            alert_type=alert_type,
            alert_id=alert_id,
            code=code,
            title=title,
            severity=severity,
            status=status,
            due_at=due_at,
            owner_id=owner_id,
            action_path=action_path,
            details=details or {},
        )

    @staticmethod
    async def inbox(
        db: AsyncSession,
        *,
        source: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> AlertInboxSummary:
        items: list[AlertInboxItem] = []

        quality_alerts = (
            await db.scalars(
                select(QualityWorkItemAlert)
                .where(QualityWorkItemAlert.deleted == 0, QualityWorkItemAlert.status != SlaAlertStatus.CLOSED)
            )
        ).all()
        for alert in quality_alerts:
            normalized_status = str(alert.status)
            severity = 'CRITICAL' if normalized_status == SlaAlertStatus.OVERDUE.value else 'HIGH'
            items.append(
                AlertService._item(
                    source='QUALITY',
                    alert_type=str(alert.entity_type),
                    alert_id=alert.id,
                    code=alert.alert_no,
                    title=alert.title,
                    severity=severity,
                    status=normalized_status,
                    due_at=alert.due_at,
                    owner_id=alert.owner_id,
                    action_path='/mes/quality',
                    details={'entity_id': alert.entity_id, 'escalation_level': alert.escalation_level},
                )
            )

        andon_events = (
            await db.scalars(
                select(ProductionAndonEvent).where(
                    ProductionAndonEvent.deleted == 0,
                    ProductionAndonEvent.status.not_in((AndonStatus.RESOLVED, AndonStatus.CANCELLED)),
                )
            )
        ).all()
        for event in andon_events:
            severity = str(event.priority)
            if severity not in {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}:
                severity = 'MEDIUM'
            items.append(
                AlertService._item(
                    source='ANDON',
                    alert_type=str(event.event_type),
                    alert_id=event.id,
                    code=event.event_no,
                    title=event.title,
                    severity=severity,
                    status=str(event.status),
                    due_at=event.sla_due_at,
                    owner_id=event.assignee_id,
                    action_path='/mes/production',
                    details={'work_order_id': event.work_order_id, 'equipment_id': event.equipment_id},
                )
            )

        replenishments = (
            await db.scalars(
                select(ReplenishmentSuggestion).where(
                    ReplenishmentSuggestion.deleted == 0,
                    ReplenishmentSuggestion.status.in_((ReplenishmentStatus.SUGGESTED, ReplenishmentStatus.FIRM)),
                    ReplenishmentSuggestion.alert_level.in_((ReplenishmentAlertLevel.SHORTAGE, ReplenishmentAlertLevel.REORDER)),
                )
            )
        ).all()
        for suggestion in replenishments:
            alert_level = str(suggestion.alert_level)
            severity = 'HIGH' if alert_level == ReplenishmentAlertLevel.SHORTAGE.value else 'MEDIUM'
            due_at = datetime.combine(suggestion.due_date, time.min)
            items.append(
                AlertService._item(
                    source='INVENTORY',
                    alert_type='REPLENISHMENT',
                    alert_id=suggestion.id,
                    code=suggestion.suggestion_no,
                    title=f'{suggestion.material_code_snapshot} 补货{alert_level}',
                    severity=severity,
                    status=alert_level,
                    due_at=due_at,
                    owner_id=None,
                    action_path='/mes/inventory/replenishment',
                    details={
                        'material_code': suggestion.material_code_snapshot,
                        'suggested_quantity': float(suggestion.suggested_quantity),
                        'order_type': str(suggestion.order_type),
                    },
                )
            )

        sales_performance = (
            await db.scalars(
                select(SalesOrderDeliveryPerformance).where(
                    SalesOrderDeliveryPerformance.deleted == 0,
                    SalesOrderDeliveryPerformance.otif_status.not_in(('OTIF',)),
                )
            )
        ).all()
        for performance in sales_performance:
            normalized_status = str(performance.otif_status)
            if normalized_status == 'OPEN':
                severity = 'HIGH'
            else:
                severity = 'CRITICAL'
            items.append(
                AlertService._item(
                    source='SALES',
                    alert_type='DELIVERY',
                    alert_id=performance.id,
                    code=f'SO-LINE-{performance.sales_order_line_id}',
                    title='销售订单交付风险',
                    severity=severity,
                    status=normalized_status,
                    due_at=performance.promised_delivery_at,
                    owner_id=None,
                    action_path='/erp/sales/delivery',
                    details={
                        'sales_order_id': performance.sales_order_id,
                        'ordered_quantity': float(performance.ordered_quantity),
                        'shipped_quantity': float(performance.shipped_quantity),
                        'delay_reason': performance.delay_reason,
                    },
                )
            )

        purchase_performance = (
            await db.scalars(
                select(PurchaseOrderDeliveryPerformance).where(
                    PurchaseOrderDeliveryPerformance.deleted == 0,
                    PurchaseOrderDeliveryPerformance.otif_status.not_in(('OTIF',)),
                )
            )
        ).all()
        for performance in purchase_performance:
            normalized_status = str(performance.otif_status)
            severity = 'HIGH' if normalized_status == 'OPEN' else 'CRITICAL'
            items.append(
                AlertService._item(
                    source='PURCHASING',
                    alert_type='SUPPLIER_DELIVERY',
                    alert_id=performance.id,
                    code=f'PO-LINE-{performance.purchase_order_line_id}',
                    title='供应商交付风险',
                    severity=severity,
                    status=normalized_status,
                    due_at=performance.effective_delivery_at,
                    owner_id=None,
                    action_path='/erp/purchasing/delivery',
                    details={
                        'purchase_order_id': performance.purchase_order_id,
                        'ordered_quantity': float(performance.ordered_quantity),
                        'received_quantity': float(performance.received_quantity),
                        'shortage_impact_quantity': float(performance.shortage_impact_quantity),
                    },
                )
            )

        if source:
            source_upper = source.upper()
            items = [item for item in items if item.source == source_upper]
        if status:
            status_upper = status.upper()
            items = [item for item in items if item.status == status_upper]

        items.sort(
            key=lambda item: (
                AlertService._priority(item.severity),
                item.due_at.timestamp() if item.due_at else float('inf'),
                item.source,
            )
        )
        items = items[:limit]
        by_source: dict[str, int] = {}
        for item in items:
            by_source[item.source] = by_source.get(item.source, 0) + 1
        return AlertInboxSummary(
            total=len(items),
            open_count=sum(item.status not in {'CLOSED', 'RESOLVED', 'CANCELLED'} for item in items),
            overdue_count=sum(item.status == 'OVERDUE' for item in items),
            by_source=by_source,
            items=items,
        )


alert_service = AlertService()
