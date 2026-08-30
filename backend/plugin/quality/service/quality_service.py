from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from math import ceil
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.model import StockTransaction
from backend.plugin.inventory.service import inventory_service
from backend.plugin.customer.model import Customer
from backend.plugin.material.model import Material
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import WorkOrder
from backend.plugin.production.schema.production import CreateWorkOrder
from backend.plugin.production.service import production_service
from backend.plugin.quality.enums import (
    AfterSalesAuditAction,
    AfterSalesExecutionStatus,
    AfterSalesRepairTaskStatus,
    CapaActionStatus,
    CapaActionType,
    CapaStatus,
    CapaVerificationResult,
    CustomerComplaintStatus,
    CustomerReturnResolution,
    CustomerReturnStatus,
    DispositionStatus,
    DispositionType,
    InspectionResult,
    InspectionStatus,
    InspectionTemplateStatus,
    InspectionType,
    NcrStatus,
    QualityConfigStatus,
    ReworkStatus,
    SlaAlertStatus,
    SlaEntityType,
)
from backend.plugin.quality.model import (
    CustomerAfterSalesAudit,
    CustomerAfterSalesOrder,
    CustomerAfterSalesRepairTask,
    QualityCapa,
    QualityCapaAction,
    QualityCapaVerification,
    CustomerComplaint,
    CustomerReturn,
    CustomerReturnLine,
    NonconformanceDisposition,
    NonconformanceReport,
    QualityInspection,
    QualityInspectionTemplate,
    QualitySamplingPlan,
    QualityReworkOrder,
    QualitySlaRule,
    QualityWorkItemAlert,
    QualityWorkItemAlertEvent,
)
from backend.plugin.quality.schema.quality import AfterSalesAuditDetail, AfterSalesOrderDetail, AfterSalesRepairTaskDetail, CapaActionDetail, CapaVerificationDetail, CompleteAfterSalesRepairTask, CompleteCustomerReturnInspection, CompleteInspection, CreateAfterSalesOrder, CreateCapa, CreateCapaAction, CreateCustomerComplaint, CreateCustomerReturn, CreateDisposition, CreateInspection, CreateNcr, CustomerComplaintDetail, CustomerReturnDetail, CustomerReturnLineDetail, OperationDashboardSummary, ReworkOrderDetail, ResolveCustomerReturn, SetCapaActionStatus, SlaRuleDetail, SupplierQualityScorecard, UpdateCapa, VerifyCapa, WorkItemAlertDetail
from backend.plugin.purchasing.model import SupplierReceipt, SupplierReceiptLine, SupplierReturn, SupplierReturnLine
from backend.plugin.routing.enums import RoutingStatus
from backend.plugin.routing.model import Routing
from backend.plugin.sales.model import Shipment, ShipmentLine
from backend.plugin.trace.enums import QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.utils.timezone import timezone


def incoming_sample_quantity(quantity: Decimal, sample_size: int) -> Decimal:
    """Return the bounded IQC sample quantity for one receipt line."""
    if quantity <= 0 or sample_size <= 0:
        raise ValueError('quantity and sample_size must be positive')
    received_units = max(1, ceil(quantity))
    return Decimal(min(sample_size, received_units))


class QualityService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def list_sla_rules(db: AsyncSession) -> Sequence[QualitySlaRule]:
        return (await db.scalars(select(QualitySlaRule).where(QualitySlaRule.deleted == 0, QualitySlaRule.active == 1).order_by(QualitySlaRule.entity_type))).all()

    @staticmethod
    async def sync_sla_alerts(db: AsyncSession) -> list[QualityWorkItemAlert]:
        """Materialize current SLA state for all five operational work-item types."""
        rules = {str(rule.entity_type): rule for rule in await QualityService.list_sla_rules(db)}
        now = timezone.now()
        work_items: list[tuple[SlaEntityType, object, str, object, object, set[str]]] = []
        ncrs = (await db.scalars(select(NonconformanceReport).where(NonconformanceReport.deleted == 0))).all()
        capas = (await db.scalars(select(QualityCapa).where(QualityCapa.deleted == 0))).all()
        complaints = (await db.scalars(select(CustomerComplaint).where(CustomerComplaint.deleted == 0))).all()
        returns = (await db.scalars(select(CustomerReturn).where(CustomerReturn.deleted == 0))).all()
        after_sales = (await db.scalars(select(CustomerAfterSalesOrder).where(CustomerAfterSalesOrder.deleted == 0))).all()
        for item in ncrs:
            work_items.append((SlaEntityType.NCR, item, item.ncr_no, item.sla_due_at, item.sla_owner_id, {NcrStatus.CLOSED.value}))
        for item in capas:
            work_items.append((SlaEntityType.CAPA, item, item.capa_no, item.due_at, item.owner_id, {CapaStatus.CLOSED.value, CapaStatus.CANCELLED.value}))
        for item in complaints:
            work_items.append((SlaEntityType.COMPLAINT, item, item.complaint_no, item.sla_due_at, item.sla_owner_id, {CustomerComplaintStatus.CLOSED.value, CustomerComplaintStatus.CANCELLED.value}))
        for item in returns:
            work_items.append((SlaEntityType.RMA, item, item.return_no, item.sla_due_at, item.sla_owner_id, {CustomerReturnStatus.CLOSED.value, CustomerReturnStatus.CANCELLED.value}))
        for item in after_sales:
            work_items.append((SlaEntityType.AFTER_SALES, item, item.execution_no, item.sla_due_at, item.sla_owner_id, {AfterSalesExecutionStatus.COMPLETED.value, AfterSalesExecutionStatus.CANCELLED.value}))
        result: list[QualityWorkItemAlert] = []
        for entity_type, item, number, due_at, owner_id, closed_statuses in work_items:
            rule = rules.get(entity_type.value)
            if not rule:
                continue
            if due_at is None:
                due_at = item.created_time + timedelta(hours=rule.target_hours)
                if hasattr(item, 'sla_due_at'):
                    item.sla_due_at = due_at
                elif hasattr(item, 'due_at'):
                    item.due_at = due_at
                if hasattr(item, 'sla_owner_id'):
                    item.sla_owner_id = owner_id or rule.default_owner_id
                elif hasattr(item, 'owner_id') and item.owner_id is None:
                    item.owner_id = rule.default_owner_id
            warning_at = due_at - timedelta(hours=max(rule.target_hours - rule.warning_hours, 0))
            alert = await db.scalar(select(QualityWorkItemAlert).where(QualityWorkItemAlert.entity_type == entity_type, QualityWorkItemAlert.entity_id == item.id, QualityWorkItemAlert.rule_id == rule.id, QualityWorkItemAlert.deleted == 0))
            if not alert:
                alert = QualityWorkItemAlert(alert_no=f'SLA-{entity_type.value}-{item.id}', entity_type=entity_type, entity_id=item.id, rule_id=rule.id, title=f'{entity_type.value} {number} SLA', due_at=due_at, owner_id=owner_id or rule.default_owner_id, warning_at=warning_at)
                db.add(alert)
            else:
                alert.due_at = due_at
                alert.warning_at = warning_at
                if owner_id:
                    alert.owner_id = owner_id
            if str(item.status) in closed_statuses:
                alert.status = SlaAlertStatus.CLOSED
                alert.resolved_at = alert.resolved_at or getattr(item, 'closed_at', None) or getattr(item, 'completed_at', None) or now
            elif alert.status not in (SlaAlertStatus.ACKNOWLEDGED, SlaAlertStatus.CLOSED):
                alert.status = SlaAlertStatus.OVERDUE if due_at <= now else (SlaAlertStatus.WARNING if warning_at <= now else SlaAlertStatus.OPEN)
            result.append(alert)
        await db.flush()
        return result

    @staticmethod
    async def list_sla_alerts(db: AsyncSession, status: str | None = None, owner_id: int | None = None) -> Sequence[QualityWorkItemAlert]:
        await QualityService.sync_sla_alerts(db)
        statement = select(QualityWorkItemAlert).where(QualityWorkItemAlert.deleted == 0)
        if status:
            statement = statement.where(QualityWorkItemAlert.status == status)
        if owner_id:
            statement = statement.where(QualityWorkItemAlert.owner_id == owner_id)
        return (await db.scalars(statement.order_by(QualityWorkItemAlert.status, QualityWorkItemAlert.due_at))).all()

    @staticmethod
    async def operation_dashboard(db: AsyncSession) -> OperationDashboardSummary:
        alerts = await QualityService.sync_sla_alerts(db)
        groups = {
            'NCR': (NonconformanceReport, 'status'), 'CAPA': (QualityCapa, 'status'),
            'COMPLAINT': (CustomerComplaint, 'status'), 'RMA': (CustomerReturn, 'status'),
            'AFTER_SALES': (CustomerAfterSalesOrder, 'status'),
        }
        status_counts: dict[str, dict[str, int]] = {}
        average_close_hours: dict[str, float] = {}
        closed_fields = {
            'NCR': ('closed_at',), 'CAPA': ('closed_at',), 'COMPLAINT': ('closed_at',),
            'RMA': ('closed_at',), 'AFTER_SALES': ('completed_at',),
        }
        for key, (model, _) in groups.items():
            rows = (await db.execute(select(model.status, func.count(model.id)).where(model.deleted == 0).group_by(model.status))).all()
            status_counts[key] = {str(status): int(count) for status, count in rows}
            close_field = getattr(model, closed_fields[key][0])
            items = (await db.execute(select(model.created_time, close_field).where(model.deleted == 0))).all()
            durations = [(closed - created).total_seconds() / 3600 for created, closed in items if created and closed]
            average_close_hours[key] = round(sum(durations) / len(durations), 2) if durations else 0.0
        overdue_counts = Counter(str(alert.entity_type) for alert in alerts if alert.status == SlaAlertStatus.OVERDUE)
        defect_rows = (await db.scalars(select(NonconformanceReport.defect_description).where(NonconformanceReport.deleted == 0, NonconformanceReport.defect_description.is_not(None)))).all()
        defect_counter = Counter(str(value).strip().lower() for value in defect_rows if str(value).strip())
        repeated_defects = [{'key': key, 'count': count} for key, count in defect_counter.most_common(10) if count > 1]
        tx_rows = (await db.scalars(select(StockTransaction.quantity_delta).where(StockTransaction.reference_type.in_(['CUSTOMER_RETURN', 'AFTER_SALES_ORDER'])))).all()
        impact = [Decimal(value or 0) for value in tx_rows]
        return OperationDashboardSummary(
            status_counts=status_counts,
            overdue_counts={key: int(overdue_counts.get(key, 0)) for key in groups},
            average_close_hours=average_close_hours,
            repeated_defects=repeated_defects,
            inventory_impact={'transaction_count': len(impact), 'quantity_delta': float(sum(impact, Decimal('0'))), 'absolute_quantity': float(sum((abs(value) for value in impact), Decimal('0')))},
            open_alerts=sum(1 for alert in alerts if alert.status != SlaAlertStatus.CLOSED),
            owner_todo_count=sum(1 for alert in alerts if alert.owner_id and alert.status not in (SlaAlertStatus.CLOSED, SlaAlertStatus.ACKNOWLEDGED)),
        )

    @staticmethod
    async def _get_alert(db: AsyncSession, alert_id: int, lock: bool = False) -> QualityWorkItemAlert:
        statement = select(QualityWorkItemAlert).where(QualityWorkItemAlert.id == alert_id, QualityWorkItemAlert.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        alert = await db.scalar(statement)
        if not alert:
            raise errors.NotFoundError(msg='QUALITY_SLA_ALERT_NOT_FOUND')
        return alert

    @staticmethod
    async def _record_alert_event(db: AsyncSession, alert: QualityWorkItemAlert, action: str, previous: SlaAlertStatus | None, notes: str | None = None) -> None:
        db.add(QualityWorkItemAlertEvent(alert_id=alert.id, action=action, from_status=previous, to_status=alert.status, notes=notes, acted_by=QualityService._operator_id(), acted_at=timezone.now()))

    @staticmethod
    async def acknowledge_sla_alert(db: AsyncSession, alert_id: int) -> WorkItemAlertDetail:
        alert = await QualityService._get_alert(db, alert_id, lock=True)
        previous = alert.status
        alert.status = SlaAlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = timezone.now()
        await QualityService._record_alert_event(db, alert, 'ACKNOWLEDGE', previous, '责任人确认 SLA 告警')
        await db.flush()
        return WorkItemAlertDetail.model_validate(alert)

    @staticmethod
    async def escalate_sla_alert(db: AsyncSession, alert_id: int, level: int = 1) -> WorkItemAlertDetail:
        alert = await QualityService._get_alert(db, alert_id, lock=True)
        previous = alert.status
        alert.status = SlaAlertStatus.OVERDUE
        alert.escalation_level = max(alert.escalation_level, level)
        alert.escalated_at = timezone.now()
        await QualityService._record_alert_event(db, alert, 'ESCALATE', previous, f'升级到第 {level} 级')
        await db.flush()
        return WorkItemAlertDetail.model_validate(alert)

    @staticmethod
    async def close_sla_alert(db: AsyncSession, alert_id: int) -> WorkItemAlertDetail:
        alert = await QualityService._get_alert(db, alert_id, lock=True)
        previous = alert.status
        alert.status = SlaAlertStatus.CLOSED
        alert.resolved_at = timezone.now()
        await QualityService._record_alert_event(db, alert, 'CLOSE', previous, '告警处理完成')
        await db.flush()
        return WorkItemAlertDetail.model_validate(alert)

    @staticmethod
    async def list_inspections(db: AsyncSession, inspection_type: str | None = None, status: str | None = None) -> Sequence[QualityInspection]:
        statement = select(QualityInspection).where(QualityInspection.deleted == 0)
        if inspection_type:
            statement = statement.where(QualityInspection.inspection_type == inspection_type)
        if status:
            statement = statement.where(QualityInspection.status == status)
        return (await db.scalars(statement.order_by(QualityInspection.created_time.desc(), QualityInspection.id.desc()))).all()

    @staticmethod
    async def supplier_scorecard(db: AsyncSession) -> list[SupplierQualityScorecard]:
        rows = (await db.execute(
            select(
                SupplierReceipt.supplier_id,
                SupplierReceipt.supplier_code_snapshot,
                SupplierReceipt.supplier_name_snapshot,
                func.count(QualityInspection.id),
                func.sum(sa.case((QualityInspection.result == InspectionResult.PASS, 1), else_=0)),
                func.sum(sa.case((QualityInspection.result.in_([InspectionResult.FAIL, InspectionResult.PARTIAL]), 1), else_=0)),
                func.coalesce(func.sum(QualityInspection.rejected_quantity), 0),
            )
            .join(QualityInspection, (QualityInspection.source_type == 'SUPPLIER_RECEIPT') & (QualityInspection.source_id == SupplierReceipt.id))
            .where(SupplierReceipt.deleted == 0, QualityInspection.deleted == 0, QualityInspection.status == InspectionStatus.COMPLETED)
            .group_by(SupplierReceipt.supplier_id, SupplierReceipt.supplier_code_snapshot, SupplierReceipt.supplier_name_snapshot)
            .order_by(SupplierReceipt.supplier_code_snapshot)
        )).all()
        result = []
        for supplier_id, code, name, total, passed, failed, rejected in rows:
            result.append(SupplierQualityScorecard(
                supplier_id=supplier_id, supplier_code=code, supplier_name=name,
                inspection_count=total, passed_count=int(passed or 0), failed_count=int(failed or 0),
                rejected_quantity=Decimal(rejected),
                pass_rate=Decimal(passed or 0) / Decimal(total) * Decimal('100') if total else Decimal('0'),
            ))
        return result

    @staticmethod
    async def get_inspection(db: AsyncSession, inspection_id: int, lock: bool = False) -> QualityInspection:
        statement = select(QualityInspection).where(QualityInspection.id == inspection_id, QualityInspection.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        inspection = await db.scalar(statement)
        if not inspection:
            raise errors.NotFoundError(msg='QUALITY_INSPECTION_NOT_FOUND')
        return inspection

    @staticmethod
    async def create_incoming_inspection(
        db: AsyncSession,
        *,
        material_id: int,
        lot: MaterialLot,
        receipt: SupplierReceipt,
        quantity: Decimal,
    ) -> QualityInspection | None:
        """Create an IQC inspection for a supplier receipt when a template is active.

        Purchasing owns receipt posting, while quality owns inspection definitions.  The
        optional runtime hook keeps that boundary intact and avoids a plugin import cycle.
        A receipt without an active incoming template remains UNINSPECTED for backwards
        compatibility; a configured template creates a pending inspection and holds the lot.
        """
        template = await db.scalar(
            select(QualityInspectionTemplate)
            .where(
                QualityInspectionTemplate.material_id == material_id,
                QualityInspectionTemplate.inspection_type == InspectionType.INCOMING,
                QualityInspectionTemplate.status == InspectionTemplateStatus.ACTIVE,
                QualityInspectionTemplate.deleted == 0,
            )
            .order_by(QualityInspectionTemplate.id.desc())
        )
        if template is None:
            return None
        if template.sampling_plan_id is None:
            raise errors.ConflictError(msg='INCOMING_TEMPLATE_SAMPLING_REQUIRED')

        plan = await db.scalar(
            select(QualitySamplingPlan).where(
                QualitySamplingPlan.id == template.sampling_plan_id,
                QualitySamplingPlan.status == QualityConfigStatus.ACTIVE,
                QualitySamplingPlan.deleted == 0,
            )
        )
        if plan is None:
            raise errors.ConflictError(msg='SAMPLING_PLAN_DISABLED')

        existing = await db.scalar(
            select(QualityInspection).where(
                QualityInspection.source_type == 'SUPPLIER_RECEIPT',
                QualityInspection.source_id == receipt.id,
                QualityInspection.material_id == material_id,
                QualityInspection.lot_id == lot.id,
                QualityInspection.inspection_type == InspectionType.INCOMING,
                QualityInspection.deleted == 0,
            )
        )
        if existing is not None:
            return existing

        sample_quantity = incoming_sample_quantity(quantity, plan.sample_size)
        inspection = QualityInspection(
            inspection_no=f'QI-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            inspection_type=InspectionType.INCOMING,
            material_id=material_id,
            lot_id=lot.id,
            source_type='SUPPLIER_RECEIPT',
            source_id=receipt.id,
            source_no=receipt.receipt_no,
            sample_quantity=sample_quantity,
        )
        db.add(inspection)
        lot.quality_status = QualityStatus.HOLD
        await db.flush()
        return inspection

    @staticmethod
    async def create_final_inspection(
        db: AsyncSession,
        *,
        material_id: int,
        lot: MaterialLot,
        source_id: int,
        source_no: str,
        quantity: Decimal,
    ) -> QualityInspection | None:
        """Create a final inspection for a finished lot when a template is active."""
        template = await db.scalar(
            select(QualityInspectionTemplate)
            .where(
                QualityInspectionTemplate.material_id == material_id,
                QualityInspectionTemplate.inspection_type == InspectionType.FINAL,
                QualityInspectionTemplate.status == InspectionTemplateStatus.ACTIVE,
                QualityInspectionTemplate.deleted == 0,
            )
            .order_by(QualityInspectionTemplate.id.desc())
        )
        if template is None:
            return None
        existing = await db.scalar(
            select(QualityInspection).where(
                QualityInspection.source_type == 'PRODUCTION_REPORT',
                QualityInspection.source_id == source_id,
                QualityInspection.material_id == material_id,
                QualityInspection.lot_id == lot.id,
                QualityInspection.inspection_type == InspectionType.FINAL,
                QualityInspection.deleted == 0,
            )
        )
        if existing is not None:
            return existing
        inspection = QualityInspection(
            inspection_no=f'QI-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            inspection_type=InspectionType.FINAL,
            material_id=material_id,
            lot_id=lot.id,
            source_type='PRODUCTION_REPORT',
            source_id=source_id,
            source_no=source_no,
            sample_quantity=quantity,
        )
        db.add(inspection)
        lot.quality_status = QualityStatus.HOLD
        await db.flush()
        return inspection

    @staticmethod
    async def create_inspection(db: AsyncSession, obj: CreateInspection) -> QualityInspection:
        material = await db.scalar(select(Material).where(Material.id == obj.material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if obj.lot_id:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == obj.lot_id, MaterialLot.deleted == 0))
            if not lot or lot.material_id != material.id:
                raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
        if obj.parent_inspection_id:
            parent = await QualityService.get_inspection(db, obj.parent_inspection_id)
            if obj.inspection_type != InspectionType.RETEST or parent.material_id != material.id:
                raise errors.ConflictError(msg='INVALID_RETEST_PARENT')
        number = (obj.inspection_no or f'QI-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        exists = await db.scalar(select(QualityInspection.id).where(QualityInspection.inspection_no == number, QualityInspection.deleted == 0))
        if exists:
            raise errors.ConflictError(msg='INSPECTION_NO_EXISTS')
        inspection = QualityInspection(inspection_no=number, **obj.model_dump(exclude={'inspection_no'}))
        db.add(inspection)
        await db.flush()
        return inspection

    @staticmethod
    async def complete_inspection(db: AsyncSession, inspection_id: int, obj: CompleteInspection) -> QualityInspection:
        inspection = await QualityService.get_inspection(db, inspection_id, lock=True)
        if inspection.status == InspectionStatus.COMPLETED:
            return inspection
        if inspection.status != InspectionStatus.PENDING:
            raise errors.ConflictError(msg='INSPECTION_NOT_PENDING')
        if obj.accepted_quantity + obj.rejected_quantity != inspection.sample_quantity:
            raise errors.RequestError(msg='INSPECTION_QUANTITY_MISMATCH')
        inspection.accepted_quantity = obj.accepted_quantity
        inspection.rejected_quantity = obj.rejected_quantity
        inspection.result = obj.result
        inspection.conclusion = obj.conclusion
        inspection.status = InspectionStatus.COMPLETED
        inspection.inspected_at = timezone.now()
        inspection.inspector_id = QualityService._operator_id()
        if inspection.lot_id:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == inspection.lot_id, MaterialLot.deleted == 0).with_for_update())
            if lot:
                lot.quality_status = QualityStatus.PASS if obj.result == InspectionResult.PASS else QualityStatus.HOLD
        if inspection.inspection_type == InspectionType.RETEST:
            rework = await db.scalar(
                select(QualityReworkOrder).where(
                    QualityReworkOrder.reinspection_id == inspection.id,
                    QualityReworkOrder.deleted == 0,
                ).with_for_update()
            )
            if rework:
                rework.status = ReworkStatus.RELEASED if obj.result == InspectionResult.PASS else ReworkStatus.AWAITING_RETEST
                if obj.result == InspectionResult.PASS:
                    rework.released_at = timezone.now()
                ncr = await QualityService.get_ncr(db, rework.ncr_id, lock=True)
                await QualityService._refresh_ncr_status(db, ncr)
            elif inspection.source_type == 'NCR' and inspection.source_id:
                ncr = await QualityService.get_ncr(db, inspection.source_id, lock=True)
                await QualityService._refresh_ncr_status(db, ncr)
        await db.flush()
        if inspection.inspection_type == InspectionType.INCOMING and inspection.source_type == 'SUPPLIER_RECEIPT':
            from backend.plugin.quality.service.sqm_service import sqm_service

            await sqm_service.assess_supplier_by_inspection(db, inspection)
        return inspection

    @staticmethod
    async def list_ncrs(db: AsyncSession, status: str | None = None) -> Sequence[NonconformanceReport]:
        statement = select(NonconformanceReport).where(NonconformanceReport.deleted == 0)
        if status:
            statement = statement.where(NonconformanceReport.status == status)
        return (await db.scalars(statement.order_by(NonconformanceReport.created_time.desc(), NonconformanceReport.id.desc()))).all()

    @staticmethod
    async def get_ncr(db: AsyncSession, ncr_id: int, lock: bool = False) -> NonconformanceReport:
        statement = select(NonconformanceReport).where(NonconformanceReport.id == ncr_id, NonconformanceReport.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        ncr = await db.scalar(statement)
        if not ncr:
            raise errors.NotFoundError(msg='NCR_NOT_FOUND')
        return ncr

    @staticmethod
    async def create_ncr(db: AsyncSession, obj: CreateNcr) -> NonconformanceReport:
        inspection = await QualityService.get_inspection(db, obj.inspection_id, lock=True)
        if inspection.status != InspectionStatus.COMPLETED or inspection.result == InspectionResult.PASS:
            raise errors.ConflictError(msg='INSPECTION_HAS_NO_NONCONFORMANCE')
        allocated = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(NonconformanceReport.nonconforming_quantity), 0)).where(
                    NonconformanceReport.inspection_id == inspection.id,
                    NonconformanceReport.deleted == 0,
                )
            )
            or 0
        )
        if allocated + obj.nonconforming_quantity > inspection.rejected_quantity:
            raise errors.ConflictError(msg='NCR_QUANTITY_EXCEEDS_REJECTED')
        number = (obj.ncr_no or f'NCR-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        ncr = NonconformanceReport(
            ncr_no=number, inspection_id=inspection.id, material_id=inspection.material_id,
            lot_id=inspection.lot_id, nonconforming_quantity=obj.nonconforming_quantity,
            defect_description=obj.defect_description, severity=obj.severity.upper(),
        )
        db.add(ncr)
        await db.flush()
        from backend.plugin.quality.service.sqm_service import sqm_service

        await sqm_service.ensure_scar_for_ncr(db, ncr)
        return ncr

    @staticmethod
    async def _refresh_ncr_status(db: AsyncSession, ncr: NonconformanceReport) -> None:
        """Move an NCR to DISPOSED only when every quantity and quality gate is complete."""
        dispositions = (
            await db.scalars(
                select(NonconformanceDisposition).where(
                    NonconformanceDisposition.ncr_id == ncr.id,
                    NonconformanceDisposition.deleted == 0,
                )
            )
        ).all()
        executed_quantity = sum(
            (item.quantity for item in dispositions if item.status == DispositionStatus.EXECUTED),
            Decimal('0'),
        )
        quality_gate_ready = True
        for item in dispositions:
            if item.status != DispositionStatus.EXECUTED:
                continue
            if item.disposition_type == DispositionType.REWORK:
                rework = await db.scalar(
                    select(QualityReworkOrder).where(
                        QualityReworkOrder.id == item.rework_order_id,
                        QualityReworkOrder.deleted == 0,
                    )
                )
                if not rework or rework.status != ReworkStatus.RELEASED:
                    quality_gate_ready = False
            elif item.disposition_type == DispositionType.REINSPECT:
                retest = await db.scalar(
                    select(QualityInspection).where(
                        QualityInspection.id == item.reinspection_id,
                        QualityInspection.deleted == 0,
                    )
                )
                if not retest or retest.status != InspectionStatus.COMPLETED or retest.result != InspectionResult.PASS:
                    quality_gate_ready = False
        if executed_quantity >= ncr.nonconforming_quantity and quality_gate_ready:
            ncr.status = NcrStatus.DISPOSED
        elif dispositions and ncr.status not in (NcrStatus.CLOSED, NcrStatus.DISPOSED):
            ncr.status = NcrStatus.UNDER_REVIEW

    @staticmethod
    async def list_dispositions(db: AsyncSession, ncr_id: int) -> Sequence[NonconformanceDisposition]:
        await QualityService.get_ncr(db, ncr_id)
        return (await db.scalars(select(NonconformanceDisposition).where(NonconformanceDisposition.ncr_id == ncr_id, NonconformanceDisposition.deleted == 0).order_by(NonconformanceDisposition.id))).all()

    @staticmethod
    async def create_disposition(db: AsyncSession, obj: CreateDisposition) -> NonconformanceDisposition:
        ncr = await QualityService.get_ncr(db, obj.ncr_id, lock=True)
        if ncr.status in (NcrStatus.DISPOSED, NcrStatus.CLOSED):
            raise errors.ConflictError(msg='NCR_NOT_DISPOSABLE')
        allocated = await db.scalar(select(func.coalesce(func.sum(NonconformanceDisposition.quantity), 0)).where(
            NonconformanceDisposition.ncr_id == ncr.id,
            NonconformanceDisposition.deleted == 0,
            NonconformanceDisposition.status != DispositionStatus.CANCELLED,
        ))
        if Decimal(allocated) + obj.quantity > ncr.nonconforming_quantity:
            raise errors.ConflictError(msg='MRB_QUANTITY_EXCEEDS_NCR')
        if obj.disposition_type in (DispositionType.SCRAP, DispositionType.RETURN_TO_SUPPLIER) and (not obj.warehouse_id or not obj.location_id):
            raise errors.RequestError(msg='MRB_STOCK_POSITION_REQUIRED')
        if obj.disposition_type in (DispositionType.REWORK, DispositionType.REINSPECT) and not ncr.lot_id:
            raise errors.ConflictError(msg='MRB_REWORK_LOT_REQUIRED')
        if obj.disposition_type == DispositionType.REWORK:
            existing_rework = await db.scalar(
                select(QualityReworkOrder.id).where(
                    QualityReworkOrder.ncr_id == ncr.id,
                    QualityReworkOrder.deleted == 0,
                )
            )
            if existing_rework:
                raise errors.ConflictError(msg='REWORK_ALREADY_EXISTS')
        number = (obj.disposition_no or f'MRB-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        disposition = NonconformanceDisposition(disposition_no=number, **obj.model_dump(exclude={'disposition_no'}))
        db.add(disposition)
        ncr.status = NcrStatus.UNDER_REVIEW
        await db.flush()
        return disposition

    @staticmethod
    async def execute_disposition(db: AsyncSession, disposition_id: int) -> NonconformanceDisposition:
        disposition = await db.scalar(select(NonconformanceDisposition).where(
            NonconformanceDisposition.id == disposition_id, NonconformanceDisposition.deleted == 0
        ).with_for_update())
        if not disposition:
            raise errors.NotFoundError(msg='MRB_DISPOSITION_NOT_FOUND')
        if disposition.status == DispositionStatus.EXECUTED:
            return disposition
        if disposition.status != DispositionStatus.APPROVED:
            raise errors.ConflictError(msg='MRB_NOT_APPROVED')
        ncr = await QualityService.get_ncr(db, disposition.ncr_id, lock=True)
        if disposition.disposition_type in (DispositionType.SCRAP, DispositionType.RETURN_TO_SUPPLIER):
            transaction = await inventory_service.post_transaction(
                db, idempotency_key=f'MRB:{disposition.id}',
                transaction_type=StockTransactionType.SCRAP if disposition.disposition_type == DispositionType.SCRAP else StockTransactionType.PURCHASE_RETURN,
                material_id=ncr.material_id, lot_id=ncr.lot_id,
                warehouse_id=disposition.warehouse_id, location_id=disposition.location_id,
                quantity_delta=-disposition.quantity, reference_type='MRB_DISPOSITION',
                reference_id=disposition.id, reference_no=disposition.disposition_no,
                remark=disposition.decision_reason, operator_id=QualityService._operator_id(),
            )
            disposition.stock_transaction_id = transaction.id
            if disposition.disposition_type == DispositionType.RETURN_TO_SUPPLIER:
                inspection = await QualityService.get_inspection(db, ncr.inspection_id)
                if inspection.source_type != 'SUPPLIER_RECEIPT' or not inspection.source_id:
                    raise errors.ConflictError(msg='SUPPLIER_RECEIPT_SOURCE_REQUIRED')
                receipt = await db.scalar(select(SupplierReceipt).where(
                    SupplierReceipt.id == inspection.source_id, SupplierReceipt.deleted == 0
                ))
                if not receipt:
                    raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_NOT_FOUND')
                receipt_line = await db.scalar(select(SupplierReceiptLine).where(
                    SupplierReceiptLine.supplier_receipt_id == receipt.id,
                    SupplierReceiptLine.material_id == ncr.material_id,
                    SupplierReceiptLine.lot_id == ncr.lot_id,
                    SupplierReceiptLine.deleted == 0,
                ))
                if not receipt_line:
                    raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_LINE_NOT_FOUND')
                supplier_return = SupplierReturn(
                    return_no=f'SRT-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}',
                    supplier_id=receipt.supplier_id,
                    supplier_receipt_id=receipt.id,
                    ncr_id=ncr.id,
                    disposition_id=disposition.id,
                    supplier_code_snapshot=receipt.supplier_code_snapshot,
                    supplier_name_snapshot=receipt.supplier_name_snapshot,
                    remark=disposition.decision_reason,
                )
                db.add(supplier_return)
                await db.flush()
                db.add(SupplierReturnLine(
                    supplier_return_id=supplier_return.id,
                    supplier_receipt_line_id=receipt_line.id if receipt_line else None,
                    material_id=ncr.material_id,
                    lot_id=ncr.lot_id,
                    warehouse_id=disposition.warehouse_id,
                    location_id=disposition.location_id,
                    quantity=disposition.quantity,
                    stock_transaction_id=transaction.id,
                ))
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == ncr.lot_id, MaterialLot.deleted == 0).with_for_update())
            if lot:
                lot.quality_status = QualityStatus.FAIL
        elif disposition.disposition_type == DispositionType.REWORK:
            rework = QualityReworkOrder(
                rework_no=f'REWORK-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
                ncr_id=ncr.id,
                material_id=ncr.material_id,
                lot_id=ncr.lot_id,
                quantity=disposition.quantity,
                remark=disposition.decision_reason,
            )
            db.add(rework)
            await db.flush()
            disposition.rework_order_id = rework.id
        elif disposition.disposition_type == DispositionType.REINSPECT:
            inspection = await QualityService.create_inspection(db, CreateInspection(
                inspection_type=InspectionType.RETEST, material_id=ncr.material_id, lot_id=ncr.lot_id,
                parent_inspection_id=ncr.inspection_id, source_type='NCR', source_id=ncr.id,
                source_no=ncr.ncr_no, sample_quantity=disposition.quantity,
            ))
            disposition.reinspection_id = inspection.id
        elif disposition.disposition_type == DispositionType.USE_AS_IS and ncr.lot_id:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == ncr.lot_id, MaterialLot.deleted == 0).with_for_update())
            if lot:
                # A partial concession cannot release the entire physical lot.
                lot.quality_status = QualityStatus.HOLD
        disposition.status = DispositionStatus.EXECUTED
        disposition.executed_at = timezone.now()
        disposition.executed_by = QualityService._operator_id()
        # The project session disables autoflush. Persist the in-transaction state
        # before aggregating dispositions so the current execution is included.
        await db.flush()
        await QualityService._refresh_ncr_status(db, ncr)
        if (
            disposition.disposition_type == DispositionType.USE_AS_IS
            and ncr.lot_id
            and ncr.status == NcrStatus.DISPOSED
        ):
            unresolved_ncr = await db.scalar(select(NonconformanceReport.id).where(
                NonconformanceReport.lot_id == ncr.lot_id,
                NonconformanceReport.id != ncr.id,
                NonconformanceReport.status.not_in((NcrStatus.DISPOSED, NcrStatus.CLOSED)),
                NonconformanceReport.deleted == 0,
            ))
            if unresolved_ncr is None:
                lot = await db.scalar(select(MaterialLot).where(
                    MaterialLot.id == ncr.lot_id,
                    MaterialLot.deleted == 0,
                ).with_for_update())
                if lot:
                    lot.quality_status = QualityStatus.PASS
        await db.flush()
        return disposition

    @staticmethod
    async def list_rework_orders(db: AsyncSession, status: str | None = None) -> Sequence[QualityReworkOrder]:
        statement = select(QualityReworkOrder).where(QualityReworkOrder.deleted == 0)
        if status:
            statement = statement.where(QualityReworkOrder.status == status)
        return (await db.scalars(statement.order_by(QualityReworkOrder.created_time.desc()))).all()

    @staticmethod
    async def create_rework_work_order(db: AsyncSession, rework_id: int) -> QualityReworkOrder:
        """Create the production execution document for one rework cycle.

        A failed retest may start another cycle; the old work order remains immutable
        and the rework task points at the newest cycle for operational convenience.
        """
        rework = await db.scalar(
            select(QualityReworkOrder).where(
                QualityReworkOrder.id == rework_id,
                QualityReworkOrder.deleted == 0,
            ).with_for_update()
        )
        if not rework:
            raise errors.NotFoundError(msg='REWORK_ORDER_NOT_FOUND')

        existing_order = None
        if rework.production_work_order_id:
            existing_order = await db.scalar(
                select(WorkOrder).where(
                    WorkOrder.id == rework.production_work_order_id,
                    WorkOrder.deleted == 0,
                ).with_for_update()
            )
            if existing_order and existing_order.status != WorkOrderStatus.COMPLETED:
                return rework
            if rework.status != ReworkStatus.AWAITING_RETEST:
                raise errors.ConflictError(msg='REWORK_WORK_ORDER_ALREADY_COMPLETED')
            if rework.reinspection_id:
                retest = await QualityService.get_inspection(db, rework.reinspection_id)
                if retest.status != InspectionStatus.COMPLETED or retest.result != InspectionResult.FAIL:
                    raise errors.ConflictError(msg='RETEST_NOT_FAILED')

        if rework.status not in (ReworkStatus.PLANNED, ReworkStatus.AWAITING_RETEST):
            raise errors.ConflictError(msg='REWORK_NOT_WORK_ORDERABLE')

        product = await db.scalar(select(Material).where(Material.id == rework.material_id, Material.deleted == 0))
        if not product or not product.producible:
            raise errors.ConflictError(msg='REWORK_PRODUCT_NOT_PRODUCIBLE')
        bom = await db.scalar(
            select(Bom).where(
                Bom.product_material_id == rework.material_id,
                Bom.status == BomStatus.ACTIVE,
                Bom.deleted == 0,
            ).order_by(Bom.is_default.desc(), Bom.id.desc())
        )
        routing = await db.scalar(
            select(Routing).where(
                Routing.product_material_id == rework.material_id,
                Routing.status == RoutingStatus.ACTIVE,
                Routing.deleted == 0,
            ).order_by(Routing.is_default.desc(), Routing.id.desc())
        )
        if not bom or not routing:
            raise errors.ConflictError(msg='REWORK_BOM_ROUTING_REQUIRED')

        detail = await production_service.create_order(
            db,
            CreateWorkOrder(
                work_order_no=f'RWO-{rework.id}-{uuid4().hex[:8]}'.upper(),
                product_material_id=rework.material_id,
                bom_id=bom.id,
                routing_id=routing.id,
                planned_quantity=rework.quantity,
                remark=f'REWORK:{rework.rework_no}',
            ),
        )
        await production_service.release_order(db, detail.id)
        rework.production_work_order_id = detail.id
        await db.flush()
        return rework

    @staticmethod
    async def start_rework(db: AsyncSession, rework_id: int) -> QualityReworkOrder:
        rework = await db.scalar(
            select(QualityReworkOrder).where(
                QualityReworkOrder.id == rework_id,
                QualityReworkOrder.deleted == 0,
            ).with_for_update()
        )
        if not rework:
            raise errors.NotFoundError(msg='REWORK_ORDER_NOT_FOUND')
        if rework.status == ReworkStatus.IN_PROGRESS:
            return rework
        if rework.status == ReworkStatus.AWAITING_RETEST and rework.reinspection_id:
            retest = await db.scalar(
                select(QualityInspection).where(
                    QualityInspection.id == rework.reinspection_id,
                    QualityInspection.deleted == 0,
                )
            )
            if retest and retest.status == InspectionStatus.COMPLETED and retest.result != InspectionResult.PASS:
                if not rework.production_work_order_id:
                    raise errors.ConflictError(msg='REWORK_WORK_ORDER_REQUIRED')
            elif retest and retest.status != InspectionStatus.COMPLETED:
                raise errors.ConflictError(msg='RETEST_PENDING')
        if rework.status != ReworkStatus.PLANNED:
            if rework.status != ReworkStatus.AWAITING_RETEST:
                raise errors.ConflictError(msg='REWORK_NOT_STARTABLE')
        if not rework.production_work_order_id:
            raise errors.ConflictError(msg='REWORK_WORK_ORDER_REQUIRED')
        work_order = await db.scalar(
            select(WorkOrder).where(
                WorkOrder.id == rework.production_work_order_id,
                WorkOrder.deleted == 0,
            ).with_for_update()
        )
        if not work_order:
            raise errors.NotFoundError(msg='REWORK_WORK_ORDER_NOT_FOUND')
        if work_order.status == WorkOrderStatus.DRAFT:
            await production_service.release_order(db, work_order.id)
            work_order.status = WorkOrderStatus.RELEASED
        if work_order.status == WorkOrderStatus.RELEASED:
            await production_service.start_order(db, work_order.id)
        elif work_order.status != WorkOrderStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='REWORK_WORK_ORDER_NOT_STARTABLE')
        rework.status = ReworkStatus.IN_PROGRESS
        rework.started_at = timezone.now()
        await db.flush()
        return rework

    @staticmethod
    async def complete_rework(db: AsyncSession, rework_id: int) -> QualityReworkOrder:
        rework = await db.scalar(
            select(QualityReworkOrder).where(
                QualityReworkOrder.id == rework_id,
                QualityReworkOrder.deleted == 0,
            ).with_for_update()
        )
        if not rework:
            raise errors.NotFoundError(msg='REWORK_ORDER_NOT_FOUND')
        if rework.status == ReworkStatus.AWAITING_RETEST:
            return rework
        if rework.status != ReworkStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='REWORK_NOT_COMPLETABLE')
        if not rework.production_work_order_id:
            raise errors.ConflictError(msg='REWORK_WORK_ORDER_REQUIRED')
        work_order = await db.scalar(
            select(WorkOrder).where(
                WorkOrder.id == rework.production_work_order_id,
                WorkOrder.deleted == 0,
            ).with_for_update()
        )
        if not work_order or work_order.status != WorkOrderStatus.COMPLETED:
            raise errors.ConflictError(msg='REWORK_WORK_ORDER_NOT_COMPLETED')
        if work_order.completed_quantity < rework.quantity:
            raise errors.ConflictError(msg='REWORK_COMPLETED_QUANTITY_INSUFFICIENT')
        ncr = await QualityService.get_ncr(db, rework.ncr_id, lock=True)
        inspection = await QualityService.create_inspection(
            db,
            CreateInspection(
                inspection_type=InspectionType.RETEST,
                material_id=rework.material_id,
                lot_id=rework.lot_id,
                parent_inspection_id=ncr.inspection_id,
                source_type='REWORK',
                source_id=rework.id,
                source_no=rework.rework_no,
                sample_quantity=rework.quantity,
            ),
        )
        rework.reinspection_id = inspection.id
        rework.status = ReworkStatus.AWAITING_RETEST
        rework.completed_at = timezone.now()
        lot = await db.scalar(
            select(MaterialLot).where(MaterialLot.id == rework.lot_id, MaterialLot.deleted == 0).with_for_update()
        )
        if lot:
            lot.quality_status = QualityStatus.HOLD
        await db.flush()
        return rework

    @staticmethod
    async def list_capas(db: AsyncSession, status: str | None = None, ncr_id: int | None = None) -> Sequence[QualityCapa]:
        statement = select(QualityCapa).where(QualityCapa.deleted == 0)
        if status:
            statement = statement.where(QualityCapa.status == status)
        if ncr_id:
            statement = statement.where(QualityCapa.ncr_id == ncr_id)
        return (await db.scalars(statement.order_by(QualityCapa.created_time.desc(), QualityCapa.id.desc()))).all()

    @staticmethod
    async def get_capa(db: AsyncSession, capa_id: int, lock: bool = False) -> QualityCapa:
        statement = select(QualityCapa).where(QualityCapa.id == capa_id, QualityCapa.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        capa = await db.scalar(statement)
        if not capa:
            raise errors.NotFoundError(msg='CAPA_NOT_FOUND')
        return capa

    @staticmethod
    async def create_capa(db: AsyncSession, obj: CreateCapa) -> QualityCapa:
        ncr = await QualityService.get_ncr(db, obj.ncr_id, lock=True)
        if ncr.status == NcrStatus.CLOSED:
            raise errors.ConflictError(msg='NCR_ALREADY_CLOSED')
        existing = await db.scalar(select(QualityCapa).where(QualityCapa.ncr_id == ncr.id, QualityCapa.deleted == 0))
        if existing:
            raise errors.ConflictError(msg='NCR_CAPA_ALREADY_EXISTS')
        number = (obj.capa_no or f'CAPA-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(QualityCapa.id).where(QualityCapa.capa_no == number, QualityCapa.deleted == 0)):
            raise errors.ConflictError(msg='CAPA_NO_EXISTS')
        capa = QualityCapa(capa_no=number, **obj.model_dump(exclude={'capa_no'}))
        db.add(capa)
        await db.flush()
        complaint = await db.scalar(select(CustomerComplaint).where(CustomerComplaint.ncr_id == ncr.id, CustomerComplaint.deleted == 0).with_for_update())
        if complaint:
            complaint.capa_id = capa.id
            complaint.status = CustomerComplaintStatus.CAPA_IN_PROGRESS
        return capa

    @staticmethod
    async def update_capa(db: AsyncSession, capa_id: int, obj: UpdateCapa) -> QualityCapa:
        capa = await QualityService.get_capa(db, capa_id, lock=True)
        if capa.status in (CapaStatus.CLOSED, CapaStatus.CANCELLED):
            raise errors.ConflictError(msg='CAPA_NOT_EDITABLE')
        for key, value in obj.model_dump(exclude_unset=True).items():
            setattr(capa, key, value)
        if capa.d4_root_cause and capa.status == CapaStatus.OPEN:
            capa.status = CapaStatus.ANALYSIS
        if capa.d5_corrective_plan and capa.status in (CapaStatus.OPEN, CapaStatus.ANALYSIS):
            capa.status = CapaStatus.ACTION
        await db.flush()
        return capa

    @staticmethod
    async def list_capa_actions(db: AsyncSession, capa_id: int) -> Sequence[QualityCapaAction]:
        await QualityService.get_capa(db, capa_id)
        return (await db.scalars(select(QualityCapaAction).where(QualityCapaAction.capa_id == capa_id, QualityCapaAction.deleted == 0).order_by(QualityCapaAction.created_time, QualityCapaAction.id))).all()

    @staticmethod
    async def create_capa_action(db: AsyncSession, capa_id: int, obj: CreateCapaAction) -> QualityCapaAction:
        capa = await QualityService.get_capa(db, capa_id, lock=True)
        if capa.status in (CapaStatus.CLOSED, CapaStatus.CANCELLED):
            raise errors.ConflictError(msg='CAPA_NOT_ACTIONABLE')
        action = QualityCapaAction(
            action_no=f'CAPA-A-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            capa_id=capa.id,
            **obj.model_dump(),
        )
        db.add(action)
        capa.status = CapaStatus.ACTION
        await db.flush()
        return action

    @staticmethod
    async def set_capa_action_status(db: AsyncSession, capa_id: int, action_id: int, obj: SetCapaActionStatus) -> QualityCapaAction:
        capa = await QualityService.get_capa(db, capa_id, lock=True)
        action = await db.scalar(select(QualityCapaAction).where(QualityCapaAction.id == action_id, QualityCapaAction.capa_id == capa.id, QualityCapaAction.deleted == 0).with_for_update())
        if not action:
            raise errors.NotFoundError(msg='CAPA_ACTION_NOT_FOUND')
        if capa.status in (CapaStatus.CLOSED, CapaStatus.CANCELLED):
            raise errors.ConflictError(msg='CAPA_NOT_ACTIONABLE')
        if action.status == obj.status:
            if obj.evidence is not None:
                action.evidence = obj.evidence
            return action
        allowed = {
            CapaActionStatus.OPEN: {CapaActionStatus.IN_PROGRESS, CapaActionStatus.COMPLETED, CapaActionStatus.CANCELLED},
            CapaActionStatus.IN_PROGRESS: {CapaActionStatus.COMPLETED, CapaActionStatus.CANCELLED},
            CapaActionStatus.COMPLETED: {CapaActionStatus.VERIFIED, CapaActionStatus.CANCELLED},
            CapaActionStatus.VERIFIED: set(),
            CapaActionStatus.CANCELLED: set(),
        }
        if obj.status not in allowed.get(action.status, set()):
            raise errors.ConflictError(msg='CAPA_ACTION_INVALID_TRANSITION')
        action.status = obj.status
        if obj.evidence is not None:
            action.evidence = obj.evidence
        if obj.status == CapaActionStatus.COMPLETED:
            action.completed_at = timezone.now()
        if obj.status == CapaActionStatus.VERIFIED:
            action.verified_at = timezone.now()
        await db.flush()
        return action

    @staticmethod
    async def list_capa_verifications(db: AsyncSession, capa_id: int) -> Sequence[QualityCapaVerification]:
        await QualityService.get_capa(db, capa_id)
        return (await db.scalars(select(QualityCapaVerification).where(QualityCapaVerification.capa_id == capa_id, QualityCapaVerification.deleted == 0).order_by(QualityCapaVerification.verified_at.desc(), QualityCapaVerification.id.desc()))).all()

    @staticmethod
    async def verify_capa(db: AsyncSession, capa_id: int, obj: VerifyCapa) -> QualityCapaVerification:
        capa = await QualityService.get_capa(db, capa_id, lock=True)
        if capa.status in (CapaStatus.CLOSED, CapaStatus.CANCELLED):
            raise errors.ConflictError(msg='CAPA_NOT_VERIFIABLE')
        actions = (await db.scalars(select(QualityCapaAction).where(QualityCapaAction.capa_id == capa.id, QualityCapaAction.deleted == 0, QualityCapaAction.status != CapaActionStatus.CANCELLED))).all()
        if obj.result == CapaVerificationResult.PASS:
            if not capa.d4_root_cause:
                raise errors.ConflictError(msg='CAPA_ROOT_CAUSE_REQUIRED')
            if not actions or any(item.status not in (CapaActionStatus.COMPLETED, CapaActionStatus.VERIFIED) for item in actions):
                raise errors.ConflictError(msg='CAPA_ACTIONS_INCOMPLETE')
            capa.status = CapaStatus.VERIFYING
        else:
            capa.status = CapaStatus.ACTION
        verification = QualityCapaVerification(
            capa_id=capa.id,
            result=obj.result,
            notes=obj.notes,
            verified_by=QualityService._operator_id(),
            verified_at=timezone.now(),
        )
        db.add(verification)
        await db.flush()
        return verification

    @staticmethod
    async def close_capa(db: AsyncSession, capa_id: int) -> QualityCapa:
        capa = await QualityService.get_capa(db, capa_id, lock=True)
        if capa.status != CapaStatus.VERIFYING:
            raise errors.ConflictError(msg='CAPA_NOT_READY_TO_CLOSE')
        latest = await db.scalar(select(QualityCapaVerification).where(QualityCapaVerification.capa_id == capa.id, QualityCapaVerification.deleted == 0).order_by(QualityCapaVerification.verified_at.desc(), QualityCapaVerification.id.desc()))
        if not latest or latest.result != CapaVerificationResult.PASS:
            raise errors.ConflictError(msg='CAPA_EFFECTIVENESS_NOT_PASSED')
        ncr = await QualityService.get_ncr(db, capa.ncr_id, lock=True)
        if ncr.status not in (NcrStatus.DISPOSED, NcrStatus.CLOSED):
            raise errors.ConflictError(msg='NCR_NOT_FULLY_DISPOSED')
        capa.status = CapaStatus.CLOSED
        capa.closed_at = timezone.now()
        await db.flush()
        return capa

    @staticmethod
    async def list_customer_complaints(db: AsyncSession, status: str | None = None) -> Sequence[CustomerComplaint]:
        statement = select(CustomerComplaint).where(CustomerComplaint.deleted == 0)
        if status:
            statement = statement.where(CustomerComplaint.status == status)
        return (await db.scalars(statement.order_by(CustomerComplaint.created_time.desc(), CustomerComplaint.id.desc()))).all()

    @staticmethod
    async def create_customer_complaint(db: AsyncSession, obj: CreateCustomerComplaint) -> CustomerComplaint:
        customer = await db.scalar(select(Customer).where(Customer.id == obj.customer_id, Customer.deleted == 0))
        if not customer:
            raise errors.NotFoundError(msg='CUSTOMER_NOT_FOUND')
        if obj.shipment_id:
            shipment = await db.scalar(select(Shipment).where(Shipment.id == obj.shipment_id, Shipment.deleted == 0))
            if not shipment or shipment.customer_id != customer.id:
                raise errors.ConflictError(msg='COMPLAINT_SHIPMENT_CUSTOMER_MISMATCH')
        number = (obj.complaint_no or f'CC-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(CustomerComplaint.id).where(CustomerComplaint.complaint_no == number, CustomerComplaint.deleted == 0)):
            raise errors.ConflictError(msg='COMPLAINT_NO_EXISTS')
        complaint = CustomerComplaint(
            complaint_no=number,
            customer_id=customer.id,
            customer_code_snapshot=customer.customer_code,
            customer_name_snapshot=customer.customer_name,
            **obj.model_dump(exclude={'complaint_no', 'customer_id'}),
        )
        db.add(complaint)
        await db.flush()
        return complaint

    @staticmethod
    async def get_customer_complaint(db: AsyncSession, complaint_id: int, lock: bool = False) -> CustomerComplaint:
        statement = select(CustomerComplaint).where(CustomerComplaint.id == complaint_id, CustomerComplaint.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        complaint = await db.scalar(statement)
        if not complaint:
            raise errors.NotFoundError(msg='CUSTOMER_COMPLAINT_NOT_FOUND')
        return complaint

    @staticmethod
    async def _customer_return_detail(db: AsyncSession, item: CustomerReturn) -> CustomerReturnDetail:
        detail = CustomerReturnDetail.model_validate(item)
        lines = (await db.scalars(select(CustomerReturnLine).where(CustomerReturnLine.return_id == item.id, CustomerReturnLine.deleted == 0).order_by(CustomerReturnLine.line_no))).all()
        detail.lines = [CustomerReturnLineDetail.model_validate(line) for line in lines]
        return detail

    @staticmethod
    async def list_customer_returns(db: AsyncSession, status: str | None = None) -> list[CustomerReturnDetail]:
        statement = select(CustomerReturn).where(CustomerReturn.deleted == 0)
        if status:
            statement = statement.where(CustomerReturn.status == status)
        returns = (await db.scalars(statement.order_by(CustomerReturn.created_time.desc(), CustomerReturn.id.desc()))).all()
        return [await QualityService._customer_return_detail(db, item) for item in returns]

    @staticmethod
    async def create_customer_return(db: AsyncSession, obj: CreateCustomerReturn) -> CustomerReturnDetail:
        complaint = await QualityService.get_customer_complaint(db, obj.complaint_id, lock=True)
        if complaint.status in (CustomerComplaintStatus.CLOSED, CustomerComplaintStatus.CANCELLED):
            raise errors.ConflictError(msg='COMPLAINT_NOT_RETURNABLE')
        if complaint.rma_id:
            raise errors.ConflictError(msg='COMPLAINT_RMA_ALREADY_EXISTS')
        shipment_id = obj.shipment_id or complaint.shipment_id
        if shipment_id:
            shipment = await db.scalar(select(Shipment).where(Shipment.id == shipment_id, Shipment.deleted == 0))
            if not shipment or shipment.customer_id != complaint.customer_id:
                raise errors.ConflictError(msg='RETURN_SHIPMENT_CUSTOMER_MISMATCH')
        number = (obj.return_no or f'RMA-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(CustomerReturn.id).where(CustomerReturn.return_no == number, CustomerReturn.deleted == 0)):
            raise errors.ConflictError(msg='RETURN_NO_EXISTS')
        item = CustomerReturn(return_no=number, complaint_id=complaint.id, customer_id=complaint.customer_id, shipment_id=shipment_id, status=CustomerReturnStatus.AUTHORIZED)
        db.add(item)
        await db.flush()
        for line_no, payload in enumerate(obj.lines, 1):
            material_id = payload.material_id
            lot_id = payload.lot_id
            if payload.shipment_line_id:
                shipment_line = await db.scalar(select(ShipmentLine).where(ShipmentLine.id == payload.shipment_line_id, ShipmentLine.deleted == 0))
                if not shipment_line or (shipment_id and shipment_line.shipment_id != shipment_id):
                    raise errors.ConflictError(msg='RETURN_SHIPMENT_LINE_INVALID')
                if shipment_line.material_id != material_id or payload.quantity > shipment_line.quantity:
                    raise errors.ConflictError(msg='RETURN_QUANTITY_EXCEEDS_SHIPMENT')
                if shipment_line.lot_id != lot_id:
                    raise errors.ConflictError(msg='RETURN_LOT_MISMATCH')
            material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
            if not material:
                raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
            if lot_id:
                lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == lot_id, MaterialLot.deleted == 0))
                if not lot or lot.material_id != material_id:
                    raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
            db.add(CustomerReturnLine(return_id=item.id, line_no=line_no, shipment_line_id=payload.shipment_line_id, material_id=material_id, lot_id=lot_id, warehouse_id=payload.warehouse_id, location_id=payload.location_id, quantity=payload.quantity))
        complaint.rma_id = item.id
        complaint.status = CustomerComplaintStatus.RMA_CREATED
        await db.flush()
        return await QualityService._customer_return_detail(db, item)

    @staticmethod
    async def receive_customer_return(db: AsyncSession, return_id: int) -> CustomerReturnDetail:
        item = await db.scalar(select(CustomerReturn).where(CustomerReturn.id == return_id, CustomerReturn.deleted == 0).with_for_update())
        if not item:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_NOT_FOUND')
        if item.status == CustomerReturnStatus.RECEIVED:
            return await QualityService._customer_return_detail(db, item)
        if item.status != CustomerReturnStatus.AUTHORIZED:
            raise errors.ConflictError(msg='CUSTOMER_RETURN_NOT_RECEIVABLE')
        lines = (await db.scalars(select(CustomerReturnLine).where(CustomerReturnLine.return_id == item.id, CustomerReturnLine.deleted == 0).with_for_update())).all()
        for line in lines:
            if line.stock_transaction_id:
                continue
            transaction = await inventory_service.post_transaction(
                db,
                idempotency_key=f'CUSTOMER_RETURN:{item.id}:{line.id}',
                transaction_type=StockTransactionType.CUSTOMER_RETURN,
                material_id=line.material_id,
                lot_id=line.lot_id,
                warehouse_id=line.warehouse_id,
                location_id=line.location_id,
                quantity_delta=line.quantity,
                reference_type='CUSTOMER_RETURN',
                reference_id=item.id,
                reference_no=item.return_no,
                operator_id=QualityService._operator_id(),
            )
            line.stock_transaction_id = transaction.id
            if line.lot_id:
                lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == line.lot_id, MaterialLot.deleted == 0).with_for_update())
                if lot:
                    lot.quality_status = QualityStatus.HOLD
        item.status = CustomerReturnStatus.RECEIVED
        item.received_at = timezone.now()
        await db.flush()
        return await QualityService._customer_return_detail(db, item)

    @staticmethod
    async def inspect_customer_return(db: AsyncSession, return_id: int, obj: CompleteCustomerReturnInspection) -> CustomerReturnDetail:
        item = await db.scalar(select(CustomerReturn).where(CustomerReturn.id == return_id, CustomerReturn.deleted == 0).with_for_update())
        if not item:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_NOT_FOUND')
        if item.status not in (CustomerReturnStatus.RECEIVED, CustomerReturnStatus.INSPECTED):
            raise errors.ConflictError(msg='CUSTOMER_RETURN_NOT_INSPECTABLE')
        line = await db.scalar(select(CustomerReturnLine).where(CustomerReturnLine.id == obj.line_id, CustomerReturnLine.return_id == item.id, CustomerReturnLine.deleted == 0).with_for_update())
        if not line:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_LINE_NOT_FOUND')
        if line.inspection_id:
            return await QualityService._customer_return_detail(db, item)
        inspection = await QualityService.create_inspection(db, CreateInspection(inspection_type=InspectionType.FINAL, material_id=line.material_id, lot_id=line.lot_id, source_type='CUSTOMER_RETURN', source_id=item.id, source_no=item.return_no, sample_quantity=line.quantity))
        await QualityService.complete_inspection(db, inspection.id, CompleteInspection(accepted_quantity=obj.accepted_quantity, rejected_quantity=obj.rejected_quantity, result=obj.result, conclusion=obj.conclusion))
        line.inspection_id = inspection.id
        if obj.result != InspectionResult.PASS and obj.rejected_quantity > 0 and not item.ncr_id:
            ncr = await QualityService.create_ncr(db, CreateNcr(ncr_no=f'NCR-{item.return_no}', inspection_id=inspection.id, nonconforming_quantity=obj.rejected_quantity, defect_description=obj.conclusion or 'Customer return nonconformance'))
            item.ncr_id = ncr.id
            complaint = await QualityService.get_customer_complaint(db, item.complaint_id, lock=True)
            complaint.ncr_id = ncr.id
            complaint.status = CustomerComplaintStatus.NCR_OPEN
        item.status = CustomerReturnStatus.INSPECTED
        item.inspected_at = timezone.now()
        await db.flush()
        return await QualityService._customer_return_detail(db, item)

    @staticmethod
    async def resolve_customer_return(db: AsyncSession, return_id: int, obj: ResolveCustomerReturn) -> CustomerReturnDetail:
        item = await db.scalar(select(CustomerReturn).where(CustomerReturn.id == return_id, CustomerReturn.deleted == 0).with_for_update())
        if not item:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_NOT_FOUND')
        if item.status == CustomerReturnStatus.RESOLVED:
            return await QualityService._customer_return_detail(db, item)
        if item.status != CustomerReturnStatus.INSPECTED:
            raise errors.ConflictError(msg='CUSTOMER_RETURN_NOT_RESOLVABLE')
        if item.ncr_id:
            ncr = await QualityService.get_ncr(db, item.ncr_id)
            if ncr.status != NcrStatus.CLOSED:
                raise errors.ConflictError(msg='RETURN_NCR_NOT_CLOSED')
        item.resolution_type = obj.resolution_type
        item.resolution_notes = obj.resolution_notes
        item.status = CustomerReturnStatus.RESOLVED
        complaint = await QualityService.get_customer_complaint(db, item.complaint_id, lock=True)
        complaint.resolution_type = obj.resolution_type
        complaint.resolution_notes = obj.resolution_notes
        complaint.status = CustomerComplaintStatus.RESOLVED
        await db.flush()
        return await QualityService._customer_return_detail(db, item)

    @staticmethod
    async def close_customer_return(db: AsyncSession, return_id: int) -> CustomerReturnDetail:
        item = await db.scalar(select(CustomerReturn).where(CustomerReturn.id == return_id, CustomerReturn.deleted == 0).with_for_update())
        if not item:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_NOT_FOUND')
        if item.status == CustomerReturnStatus.CLOSED:
            return await QualityService._customer_return_detail(db, item)
        if item.status != CustomerReturnStatus.RESOLVED:
            raise errors.ConflictError(msg='CUSTOMER_RETURN_NOT_READY_TO_CLOSE')
        if item.resolution_type not in (None, CustomerReturnResolution.NO_DEFECT):
            execution = await db.scalar(select(CustomerAfterSalesOrder).where(CustomerAfterSalesOrder.return_id == item.id, CustomerAfterSalesOrder.resolution_type == item.resolution_type, CustomerAfterSalesOrder.status == AfterSalesExecutionStatus.COMPLETED, CustomerAfterSalesOrder.deleted == 0))
            if not execution:
                raise errors.ConflictError(msg='AFTER_SALES_EXECUTION_NOT_COMPLETED')
        item.status = CustomerReturnStatus.CLOSED
        item.closed_at = timezone.now()
        complaint = await QualityService.get_customer_complaint(db, item.complaint_id, lock=True)
        complaint.status = CustomerComplaintStatus.CLOSED
        complaint.closed_at = timezone.now()
        await db.flush()
        return await QualityService._customer_return_detail(db, item)

    @staticmethod
    async def _after_sales(db: AsyncSession, order_id: int, lock: bool = False) -> CustomerAfterSalesOrder:
        statement = select(CustomerAfterSalesOrder).where(CustomerAfterSalesOrder.id == order_id, CustomerAfterSalesOrder.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        order = await db.scalar(statement)
        if not order:
            raise errors.NotFoundError(msg='AFTER_SALES_ORDER_NOT_FOUND')
        return order

    @staticmethod
    async def _after_sales_detail(db: AsyncSession, order: CustomerAfterSalesOrder) -> AfterSalesOrderDetail:
        return AfterSalesOrderDetail.model_validate(order)

    @staticmethod
    async def _after_sales_audit(db: AsyncSession, order: CustomerAfterSalesOrder, action: AfterSalesAuditAction, from_status: AfterSalesExecutionStatus | None = None, notes: str | None = None) -> None:
        db.add(CustomerAfterSalesAudit(after_sales_order_id=order.id, action=action, from_status=from_status, to_status=order.status, notes=notes, acted_by=QualityService._operator_id(), acted_at=timezone.now()))
        await db.flush()

    @staticmethod
    async def list_after_sales_orders(db: AsyncSession, status: str | None = None) -> list[AfterSalesOrderDetail]:
        statement = select(CustomerAfterSalesOrder).where(CustomerAfterSalesOrder.deleted == 0)
        if status:
            statement = statement.where(CustomerAfterSalesOrder.status == status)
        rows = (await db.scalars(statement.order_by(CustomerAfterSalesOrder.created_time.desc(), CustomerAfterSalesOrder.id.desc()))).all()
        return [await QualityService._after_sales_detail(db, row) for row in rows]

    @staticmethod
    async def list_after_sales_audits(db: AsyncSession, order_id: int) -> list[AfterSalesAuditDetail]:
        await QualityService._after_sales(db, order_id)
        rows = (await db.scalars(select(CustomerAfterSalesAudit).where(CustomerAfterSalesAudit.after_sales_order_id == order_id, CustomerAfterSalesAudit.deleted == 0).order_by(CustomerAfterSalesAudit.acted_at, CustomerAfterSalesAudit.id))).all()
        return [AfterSalesAuditDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_after_sales_order(db: AsyncSession, return_id: int, obj: CreateAfterSalesOrder) -> AfterSalesOrderDetail:
        returned = await db.scalar(select(CustomerReturn).where(CustomerReturn.id == return_id, CustomerReturn.deleted == 0).with_for_update())
        if not returned:
            raise errors.NotFoundError(msg='CUSTOMER_RETURN_NOT_FOUND')
        if returned.status != CustomerReturnStatus.RESOLVED:
            raise errors.ConflictError(msg='RMA_NOT_READY_FOR_AFTER_SALES')
        if obj.resolution_type == CustomerReturnResolution.NO_DEFECT:
            raise errors.ConflictError(msg='NO_DEFECT_NEEDS_NO_EXECUTION_ORDER')
        if await db.scalar(select(CustomerAfterSalesOrder.id).where(CustomerAfterSalesOrder.return_id == return_id, CustomerAfterSalesOrder.resolution_type == obj.resolution_type, CustomerAfterSalesOrder.deleted == 0)):
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_ALREADY_EXISTS')
        line = await db.scalar(select(CustomerReturnLine).where(CustomerReturnLine.return_id == return_id, CustomerReturnLine.deleted == 0).order_by(CustomerReturnLine.line_no))
        if not line:
            raise errors.ConflictError(msg='RMA_LINE_REQUIRED')
        quantity = obj.quantity or line.quantity
        if quantity > line.quantity:
            raise errors.ConflictError(msg='AFTER_SALES_QUANTITY_EXCEEDS_RMA')
        if obj.resolution_type == CustomerReturnResolution.REPLACEMENT and not obj.replacement_material_id:
            raise errors.RequestError(msg='REPLACEMENT_MATERIAL_REQUIRED')
        if obj.replacement_lot_id:
            replacement_lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == obj.replacement_lot_id, MaterialLot.deleted == 0))
            if not replacement_lot or replacement_lot.material_id != obj.replacement_material_id:
                raise errors.ConflictError(msg='REPLACEMENT_LOT_MATERIAL_MISMATCH')
        execution_no = (obj.execution_no or f'AS-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(CustomerAfterSalesOrder.id).where(CustomerAfterSalesOrder.execution_no == execution_no, CustomerAfterSalesOrder.deleted == 0)):
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_NO_EXISTS')
        complaint = await QualityService.get_customer_complaint(db, returned.complaint_id)
        order = CustomerAfterSalesOrder(execution_no=execution_no, return_id=returned.id, complaint_id=returned.complaint_id, sales_order_id=complaint.sales_order_id, customer_id=returned.customer_id, resolution_type=obj.resolution_type, material_id=line.material_id, lot_id=line.lot_id, warehouse_id=line.warehouse_id, location_id=line.location_id, quantity=quantity, replacement_material_id=obj.replacement_material_id, replacement_lot_id=obj.replacement_lot_id, replacement_quantity=obj.replacement_quantity or quantity if obj.resolution_type == CustomerReturnResolution.REPLACEMENT else None, execution_notes=obj.execution_notes, status=AfterSalesExecutionStatus.DRAFT)
        db.add(order)
        await db.flush()
        await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.CREATED, None, '售后执行单创建')
        return await QualityService._after_sales_detail(db, order)

    @staticmethod
    async def approve_after_sales_order(db: AsyncSession, order_id: int) -> AfterSalesOrderDetail:
        order = await QualityService._after_sales(db, order_id, lock=True)
        if order.status == AfterSalesExecutionStatus.APPROVED:
            return await QualityService._after_sales_detail(db, order)
        if order.status != AfterSalesExecutionStatus.DRAFT:
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_NOT_APPROVABLE')
        previous = order.status
        order.status = AfterSalesExecutionStatus.APPROVED
        await db.flush()
        await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.APPROVED, previous, '售后执行单审批')
        return await QualityService._after_sales_detail(db, order)

    @staticmethod
    async def start_after_sales_order(db: AsyncSession, order_id: int) -> AfterSalesOrderDetail:
        order = await QualityService._after_sales(db, order_id, lock=True)
        if order.status == AfterSalesExecutionStatus.IN_PROGRESS:
            return await QualityService._after_sales_detail(db, order)
        if order.status != AfterSalesExecutionStatus.APPROVED:
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_NOT_STARTABLE')
        previous = order.status
        order.status = AfterSalesExecutionStatus.IN_PROGRESS
        await db.flush()
        await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.STARTED, previous, '售后执行开始')
        if order.resolution_type == CustomerReturnResolution.REPAIR:
            task = CustomerAfterSalesRepairTask(task_no=f'REPAIR-{order.execution_no}', after_sales_order_id=order.id, description=order.execution_notes or '客户退货维修任务')
            db.add(task)
            await db.flush()
            await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.REPAIR_TASK_CREATED, order.status, task.task_no)
        return await QualityService._after_sales_detail(db, order)

    @staticmethod
    async def get_after_sales_repair_task(db: AsyncSession, order_id: int) -> AfterSalesRepairTaskDetail:
        await QualityService._after_sales(db, order_id)
        task = await db.scalar(select(CustomerAfterSalesRepairTask).where(CustomerAfterSalesRepairTask.after_sales_order_id == order_id, CustomerAfterSalesRepairTask.deleted == 0))
        if not task:
            raise errors.NotFoundError(msg='AFTER_SALES_REPAIR_TASK_NOT_FOUND')
        return AfterSalesRepairTaskDetail.model_validate(task)

    @staticmethod
    async def complete_after_sales_repair_task(db: AsyncSession, order_id: int, obj: CompleteAfterSalesRepairTask) -> AfterSalesRepairTaskDetail:
        order = await QualityService._after_sales(db, order_id, lock=True)
        task = await db.scalar(select(CustomerAfterSalesRepairTask).where(CustomerAfterSalesRepairTask.after_sales_order_id == order_id, CustomerAfterSalesRepairTask.deleted == 0).with_for_update())
        if not task:
            raise errors.NotFoundError(msg='AFTER_SALES_REPAIR_TASK_NOT_FOUND')
        if order.status != AfterSalesExecutionStatus.IN_PROGRESS or task.status != AfterSalesRepairTaskStatus.OPEN:
            raise errors.ConflictError(msg='AFTER_SALES_REPAIR_TASK_NOT_COMPLETABLE')
        task.status = AfterSalesRepairTaskStatus.COMPLETED
        task.result_notes = obj.result_notes
        task.started_at = task.started_at or timezone.now()
        task.completed_at = timezone.now()
        await db.flush()
        return AfterSalesRepairTaskDetail.model_validate(task)

    @staticmethod
    async def complete_after_sales_order(db: AsyncSession, order_id: int) -> AfterSalesOrderDetail:
        order = await QualityService._after_sales(db, order_id, lock=True)
        if order.status == AfterSalesExecutionStatus.COMPLETED:
            return await QualityService._after_sales_detail(db, order)
        if order.status != AfterSalesExecutionStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_NOT_COMPLETABLE')
        if order.resolution_type == CustomerReturnResolution.REPAIR:
            task = await db.scalar(select(CustomerAfterSalesRepairTask).where(CustomerAfterSalesRepairTask.after_sales_order_id == order.id, CustomerAfterSalesRepairTask.deleted == 0))
            if not task or task.status != AfterSalesRepairTaskStatus.COMPLETED:
                raise errors.ConflictError(msg='AFTER_SALES_REPAIR_TASK_NOT_COMPLETED')
        if order.resolution_type in (CustomerReturnResolution.REPLACEMENT, CustomerReturnResolution.SCRAP) and not order.stock_transaction_id:
            transaction_type = StockTransactionType.SHIPMENT if order.resolution_type == CustomerReturnResolution.REPLACEMENT else StockTransactionType.SCRAP
            material_id = order.replacement_material_id if order.resolution_type == CustomerReturnResolution.REPLACEMENT else order.material_id
            lot_id = order.replacement_lot_id if order.resolution_type == CustomerReturnResolution.REPLACEMENT else order.lot_id
            quantity = order.replacement_quantity if order.resolution_type == CustomerReturnResolution.REPLACEMENT else order.quantity
            transaction = await inventory_service.post_transaction(db, idempotency_key=f'AFTER_SALES:{order.id}', transaction_type=transaction_type, material_id=material_id, lot_id=lot_id, warehouse_id=order.warehouse_id, location_id=order.location_id, quantity_delta=-quantity, reference_type='AFTER_SALES_ORDER', reference_id=order.id, reference_no=order.execution_no, operator_id=QualityService._operator_id())
            order.stock_transaction_id = transaction.id
            await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.STOCK_POSTED, order.status, transaction.transaction_no)
        previous = order.status
        order.status = AfterSalesExecutionStatus.COMPLETED
        order.completed_at = timezone.now()
        await db.flush()
        await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.COMPLETED, previous, '售后处理执行完成')
        return await QualityService._after_sales_detail(db, order)

    @staticmethod
    async def cancel_after_sales_order(db: AsyncSession, order_id: int) -> AfterSalesOrderDetail:
        order = await QualityService._after_sales(db, order_id, lock=True)
        if order.status in (AfterSalesExecutionStatus.COMPLETED, AfterSalesExecutionStatus.CANCELLED):
            raise errors.ConflictError(msg='AFTER_SALES_ORDER_NOT_CANCELLABLE')
        previous = order.status
        order.status = AfterSalesExecutionStatus.CANCELLED
        task = await db.scalar(select(CustomerAfterSalesRepairTask).where(CustomerAfterSalesRepairTask.after_sales_order_id == order.id, CustomerAfterSalesRepairTask.deleted == 0))
        if task and task.status != AfterSalesRepairTaskStatus.COMPLETED:
            task.status = AfterSalesRepairTaskStatus.CANCELLED
        await db.flush()
        await QualityService._after_sales_audit(db, order, AfterSalesAuditAction.CANCELLED, previous, '售后执行单取消')
        return await QualityService._after_sales_detail(db, order)

    @staticmethod
    async def close_ncr(db: AsyncSession, ncr_id: int, root_cause: str | None = None) -> NonconformanceReport:
        ncr = await QualityService.get_ncr(db, ncr_id, lock=True)
        if ncr.status != NcrStatus.DISPOSED:
            raise errors.ConflictError(msg='NCR_NOT_FULLY_DISPOSED')
        capa = await db.scalar(select(QualityCapa).where(QualityCapa.ncr_id == ncr.id, QualityCapa.deleted == 0))
        if capa and capa.status != CapaStatus.CLOSED:
            raise errors.ConflictError(msg='NCR_CAPA_NOT_CLOSED')
        ncr.status = NcrStatus.CLOSED
        ncr.root_cause = root_cause
        ncr.closed_at = timezone.now()
        await db.flush()
        return ncr


quality_service = QualityService()
