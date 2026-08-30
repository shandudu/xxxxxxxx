import math
from collections import deque
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.inventory.enums import (
    ExpiryAlertLevel,
    ExpiryAlertStatus,
    LotHoldReason,
    LotHoldStatus,
    LotRecallStatus,
    RecallItemStatus,
    RecallItemType,
    ShelfLifePolicyStatus,
)
from backend.plugin.inventory.model import InventoryBalance
from backend.plugin.inventory.model.shelf_life import (
    LotExpiryAlert,
    LotQualityHold,
    LotRecall,
    LotRecallItem,
    ShelfLifePolicy,
)
from backend.plugin.inventory.schema.shelf_life import (
    CreateLotRecall,
    ExpiryAlertDetail,
    FefoCandidateDetail,
    LotHoldDetail,
    LotRecallDetail,
    RecallItemDetail,
    ReleaseLotHold,
    ScrapLotHold,
    ShelfLifeDashboard,
    ShelfLifePolicyDetail,
    ShelfLifePolicyUpsert,
    UpdateRecallItem,
)
from backend.plugin.material.model import Material
from backend.plugin.sales.model import Shipment, ShipmentLine
from backend.plugin.trace.enums import LotStatus, QualityStatus, TraceObjectType
from backend.plugin.trace.model import MaterialLot, TraceRelation
from backend.utils.timezone import timezone


ACTIVE_HOLD_STATUSES = (LotHoldStatus.OPEN, LotHoldStatus.AWAITING_RETEST)


class ShelfLifeService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _days_remaining(expiry_date, now) -> int:
        return math.ceil((expiry_date - now).total_seconds() / 86400)

    @staticmethod
    async def list_policies(db: AsyncSession) -> list[ShelfLifePolicyDetail]:
        rows = (await db.scalars(select(ShelfLifePolicy).where(
            ShelfLifePolicy.deleted == 0
        ).order_by(ShelfLifePolicy.material_id))).all()
        return [ShelfLifePolicyDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_policy(
        db: AsyncSession, material_id: int, obj: ShelfLifePolicyUpsert
    ) -> ShelfLifePolicyDetail:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        policy = await db.scalar(select(ShelfLifePolicy).where(
            ShelfLifePolicy.material_id == material_id,
            ShelfLifePolicy.deleted == 0,
        ).with_for_update())
        if policy is None:
            policy = ShelfLifePolicy(material_id=material_id, **obj.model_dump())
            db.add(policy)
        else:
            for key, value in obj.model_dump().items():
                setattr(policy, key, value)
        await db.flush()
        return ShelfLifePolicyDetail.model_validate(policy)

    @staticmethod
    async def _ensure_hold(
        db: AsyncSession,
        lot: MaterialLot,
        *,
        reason: LotHoldReason,
        source_type: str,
        source_id: int | None,
        source_no: str | None,
    ) -> LotQualityHold:
        hold = await db.scalar(select(LotQualityHold).where(
            LotQualityHold.lot_id == lot.id,
            LotQualityHold.reason == reason,
            LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
            LotQualityHold.deleted == 0,
        ).with_for_update())
        if hold is None:
            hold = LotQualityHold(
                hold_no=f'HOLD-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
                lot_id=lot.id,
                reason=reason,
                held_at=timezone.now(),
                source_type=source_type,
                source_id=source_id,
                source_no=source_no,
                original_expiry_date=lot.expiry_date,
                previous_lot_status=getattr(lot.status, 'value', lot.status),
                previous_quality_status=getattr(lot.quality_status, 'value', lot.quality_status),
            )
            db.add(hold)
        lot.status = LotStatus.HOLD
        lot.quality_status = QualityStatus.HOLD
        await db.flush()
        return hold

    @staticmethod
    async def sync_expiry_alerts(db: AsyncSession) -> list[ExpiryAlertDetail]:
        now = timezone.now()
        result = await db.execute(
            select(
                ShelfLifePolicy,
                MaterialLot,
                func.sum(InventoryBalance.quantity).label('on_hand'),
                func.sum(InventoryBalance.quantity - InventoryBalance.reserved_quantity).label('available'),
            )
            .join(MaterialLot, MaterialLot.material_id == ShelfLifePolicy.material_id)
            .join(InventoryBalance, InventoryBalance.lot_id == MaterialLot.id)
            .where(
                ShelfLifePolicy.status == ShelfLifePolicyStatus.ACTIVE,
                ShelfLifePolicy.deleted == 0,
                MaterialLot.expiry_date.is_not(None),
                MaterialLot.deleted == 0,
                InventoryBalance.deleted == 0,
            )
            .group_by(ShelfLifePolicy.id, MaterialLot.id)
            .having(func.sum(InventoryBalance.quantity) > 0)
        )
        seen_lot_ids: set[int] = set()
        alerts: list[LotExpiryAlert] = []
        for policy, lot, _on_hand, available in result.all():
            days = ShelfLifeService._days_remaining(lot.expiry_date, now)
            level = None
            if days <= 0:
                level = ExpiryAlertLevel.EXPIRED
            elif days <= policy.critical_days:
                level = ExpiryAlertLevel.CRITICAL
            elif days <= policy.warning_days:
                level = ExpiryAlertLevel.WARNING
            if level is None:
                continue
            seen_lot_ids.add(lot.id)
            alert = await db.scalar(select(LotExpiryAlert).where(
                LotExpiryAlert.lot_id == lot.id,
                LotExpiryAlert.deleted == 0,
            ).with_for_update())
            if alert is None:
                alert = LotExpiryAlert(
                    policy_id=policy.id,
                    lot_id=lot.id,
                    level=level,
                    days_remaining=days,
                    available_quantity=max(Decimal(available or 0), Decimal('0')),
                    triggered_at=now,
                )
                db.add(alert)
                await db.flush()
            else:
                alert.policy_id = policy.id
                alert.level = level
                alert.days_remaining = days
                alert.available_quantity = max(Decimal(available or 0), Decimal('0'))
                if alert.status == ExpiryAlertStatus.CLOSED:
                    alert.status = ExpiryAlertStatus.OPEN
                    alert.triggered_at = now
                    alert.resolved_at = None
            if level == ExpiryAlertLevel.EXPIRED and policy.auto_hold_expired:
                await ShelfLifeService._ensure_hold(
                    db,
                    lot,
                    reason=LotHoldReason.EXPIRED,
                    source_type='EXPIRY_ALERT',
                    source_id=alert.id,
                    source_no=f'EXP-{lot.lot_no}',
                )
            alerts.append(alert)
        active_alerts = (await db.scalars(select(LotExpiryAlert).where(
            LotExpiryAlert.status != ExpiryAlertStatus.CLOSED,
            LotExpiryAlert.deleted == 0,
        ).with_for_update())).all()
        for alert in active_alerts:
            if alert.lot_id not in seen_lot_ids:
                alert.status = ExpiryAlertStatus.CLOSED
                alert.resolved_at = now
        await db.flush()
        return [ExpiryAlertDetail.model_validate(row) for row in alerts]

    @staticmethod
    async def list_alerts(
        db: AsyncSession, status: str | None = None, level: str | None = None
    ) -> list[ExpiryAlertDetail]:
        statement = select(LotExpiryAlert).where(LotExpiryAlert.deleted == 0)
        if status:
            statement = statement.where(LotExpiryAlert.status == status)
        if level:
            statement = statement.where(LotExpiryAlert.level == level)
        rows = (await db.scalars(statement.order_by(
            LotExpiryAlert.days_remaining, LotExpiryAlert.triggered_at.desc()
        ))).all()
        return [ExpiryAlertDetail.model_validate(row) for row in rows]

    @staticmethod
    async def acknowledge_alert(db: AsyncSession, alert_id: int) -> ExpiryAlertDetail:
        alert = await db.scalar(select(LotExpiryAlert).where(
            LotExpiryAlert.id == alert_id, LotExpiryAlert.deleted == 0
        ).with_for_update())
        if not alert:
            raise errors.NotFoundError(msg='EXPIRY_ALERT_NOT_FOUND')
        if alert.status != ExpiryAlertStatus.CLOSED:
            alert.status = ExpiryAlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = ShelfLifeService._operator_id()
        await db.flush()
        return ExpiryAlertDetail.model_validate(alert)

    @staticmethod
    async def ensure_lot_issuable(db: AsyncSession, lot_id: int) -> MaterialLot:
        now = timezone.now()
        lot = await db.scalar(select(MaterialLot).where(
            MaterialLot.id == lot_id, MaterialLot.deleted == 0
        ).with_for_update())
        if not lot:
            raise errors.NotFoundError(msg='LOT_NOT_FOUND')
        if lot.status != LotStatus.ACTIVE:
            raise errors.ConflictError(msg='LOT_ISOLATED_OR_INACTIVE')
        if lot.quality_status != QualityStatus.PASS:
            raise errors.ConflictError(msg='LOT_QUALITY_NOT_PASSED')
        hold = await db.scalar(select(LotQualityHold.id).where(
            LotQualityHold.lot_id == lot.id,
            LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
            LotQualityHold.deleted == 0,
        ))
        if hold:
            raise errors.ConflictError(msg='LOT_QUALITY_HOLD_ACTIVE')
        policy = await db.scalar(select(ShelfLifePolicy).where(
            ShelfLifePolicy.material_id == lot.material_id,
            ShelfLifePolicy.status == ShelfLifePolicyStatus.ACTIVE,
            ShelfLifePolicy.deleted == 0,
        ))
        if policy:
            if lot.expiry_date is None:
                raise errors.ConflictError(msg='LOT_EXPIRY_REQUIRED')
            cutoff = now + timedelta(days=policy.min_remaining_days_at_issue)
            if lot.expiry_date <= now:
                raise errors.ConflictError(msg='LOT_EXPIRED')
            if lot.expiry_date <= cutoff:
                raise errors.ConflictError(msg='LOT_REMAINING_SHELF_LIFE_INSUFFICIENT')
        elif lot.expiry_date is not None and lot.expiry_date <= now:
            raise errors.ConflictError(msg='LOT_EXPIRED')
        return lot

    @staticmethod
    async def fefo_candidates(
        db: AsyncSession,
        *,
        material_id: int,
        warehouse_id: int,
        quantity: Decimal,
        lock: bool = False,
    ) -> list[FefoCandidateDetail]:
        policy = await db.scalar(select(ShelfLifePolicy).where(
            ShelfLifePolicy.material_id == material_id,
            ShelfLifePolicy.status == ShelfLifePolicyStatus.ACTIVE,
            ShelfLifePolicy.fefo_enabled.is_(True),
            ShelfLifePolicy.deleted == 0,
        ))
        if not policy:
            raise errors.ConflictError(msg='FEFO_POLICY_NOT_ACTIVE')
        now = timezone.now()
        cutoff = now + timedelta(days=policy.min_remaining_days_at_issue)
        active_hold = select(LotQualityHold.id).where(
            LotQualityHold.lot_id == MaterialLot.id,
            LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
            LotQualityHold.deleted == 0,
        ).exists()
        statement = (
            select(InventoryBalance, MaterialLot)
            .join(MaterialLot, MaterialLot.id == InventoryBalance.lot_id)
            .where(
                InventoryBalance.material_id == material_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.quantity > InventoryBalance.reserved_quantity,
                InventoryBalance.deleted == 0,
                MaterialLot.status == LotStatus.ACTIVE,
                MaterialLot.quality_status == QualityStatus.PASS,
                MaterialLot.expiry_date.is_not(None),
                MaterialLot.expiry_date > cutoff,
                MaterialLot.deleted == 0,
                ~active_hold,
            )
            .order_by(
                MaterialLot.expiry_date,
                MaterialLot.production_date,
                MaterialLot.lot_no,
                InventoryBalance.location_id,
            )
        )
        if lock:
            statement = statement.with_for_update()
        rows = (await db.execute(statement)).all()
        remaining = quantity
        candidates: list[FefoCandidateDetail] = []
        for balance, lot in rows:
            available = balance.quantity - balance.reserved_quantity
            allocated = min(available, remaining) if remaining > 0 else Decimal('0')
            if allocated <= 0:
                continue
            candidates.append(FefoCandidateDetail(
                balance_id=balance.id,
                lot_id=lot.id,
                lot_no=lot.lot_no,
                warehouse_id=balance.warehouse_id,
                location_id=balance.location_id,
                expiry_date=lot.expiry_date,
                days_remaining=ShelfLifeService._days_remaining(lot.expiry_date, now),
                available_quantity=available,
                allocated_quantity=allocated,
            ))
            remaining -= allocated
            if remaining <= 0:
                break
        if remaining > 0:
            raise errors.ConflictError(msg='FEFO_STOCK_INSUFFICIENT')
        return candidates

    @staticmethod
    async def list_holds(db: AsyncSession, status: str | None = None) -> list[LotHoldDetail]:
        statement = select(LotQualityHold).where(LotQualityHold.deleted == 0)
        if status:
            statement = statement.where(LotQualityHold.status == status)
        rows = (await db.scalars(statement.order_by(LotQualityHold.held_at.desc()))).all()
        return [LotHoldDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_reinspection(db: AsyncSession, hold_id: int) -> LotHoldDetail:
        hold = await db.scalar(select(LotQualityHold).where(
            LotQualityHold.id == hold_id, LotQualityHold.deleted == 0
        ).with_for_update())
        if not hold:
            raise errors.NotFoundError(msg='LOT_HOLD_NOT_FOUND')
        if hold.status == LotHoldStatus.AWAITING_RETEST and hold.inspection_id:
            return LotHoldDetail.model_validate(hold)
        if hold.status != LotHoldStatus.OPEN or hold.reason != LotHoldReason.EXPIRED:
            raise errors.ConflictError(msg='LOT_HOLD_NOT_REINSPECTABLE')
        quantity = Decimal(await db.scalar(select(func.coalesce(func.sum(InventoryBalance.quantity), 0)).where(
            InventoryBalance.lot_id == hold.lot_id,
            InventoryBalance.quantity > 0,
            InventoryBalance.deleted == 0,
        )) or 0)
        if quantity <= 0:
            raise errors.ConflictError(msg='LOT_HOLD_HAS_NO_STOCK')
        lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == hold.lot_id, MaterialLot.deleted == 0))
        from backend.plugin.quality.enums import InspectionType
        from backend.plugin.quality.schema.quality import CreateInspection
        from backend.plugin.quality.service import quality_service

        inspection = await quality_service.create_inspection(db, CreateInspection(
            inspection_type=InspectionType.RETEST,
            material_id=lot.material_id,
            lot_id=lot.id,
            source_type='LOT_EXPIRY_HOLD',
            source_id=hold.id,
            source_no=hold.hold_no,
            sample_quantity=quantity,
        ))
        hold.inspection_id = inspection.id
        hold.status = LotHoldStatus.AWAITING_RETEST
        await db.flush()
        return LotHoldDetail.model_validate(hold)

    @staticmethod
    async def release_hold(db: AsyncSession, hold_id: int, obj: ReleaseLotHold) -> LotHoldDetail:
        hold = await db.scalar(select(LotQualityHold).where(
            LotQualityHold.id == hold_id, LotQualityHold.deleted == 0
        ).with_for_update())
        if not hold:
            raise errors.NotFoundError(msg='LOT_HOLD_NOT_FOUND')
        if hold.status == LotHoldStatus.RELEASED:
            return LotHoldDetail.model_validate(hold)
        if hold.reason != LotHoldReason.EXPIRED or hold.status != LotHoldStatus.AWAITING_RETEST:
            raise errors.ConflictError(msg='LOT_HOLD_NOT_RELEASABLE')
        from backend.plugin.quality.enums import InspectionResult, InspectionStatus
        from backend.plugin.quality.model import QualityInspection

        inspection = await db.scalar(select(QualityInspection).where(
            QualityInspection.id == hold.inspection_id, QualityInspection.deleted == 0
        ))
        if not inspection or inspection.status != InspectionStatus.COMPLETED or inspection.result != InspectionResult.PASS:
            raise errors.ConflictError(msg='LOT_RETEST_NOT_PASSED')
        now = timezone.now()
        if obj.new_expiry_date <= now:
            raise errors.ConflictError(msg='NEW_EXPIRY_DATE_INVALID')
        lot = await db.scalar(select(MaterialLot).where(
            MaterialLot.id == hold.lot_id, MaterialLot.deleted == 0
        ).with_for_update())
        lot.expiry_date = obj.new_expiry_date
        hold.new_expiry_date = obj.new_expiry_date
        hold.status = LotHoldStatus.RELEASED
        hold.decided_at = now
        hold.decided_by = ShelfLifeService._operator_id()
        hold.decision_reason = obj.decision_reason
        other_hold = await db.scalar(select(LotQualityHold.id).where(
            LotQualityHold.lot_id == lot.id,
            LotQualityHold.id != hold.id,
            LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
            LotQualityHold.deleted == 0,
        ))
        if not other_hold:
            lot.status = LotStatus.ACTIVE
            lot.quality_status = QualityStatus.PASS
        alert = await db.scalar(select(LotExpiryAlert).where(
            LotExpiryAlert.lot_id == lot.id, LotExpiryAlert.deleted == 0
        ).with_for_update())
        if alert:
            alert.status = ExpiryAlertStatus.CLOSED
            alert.resolved_at = now
        await db.flush()
        return LotHoldDetail.model_validate(hold)

    @staticmethod
    async def scrap_hold(db: AsyncSession, hold_id: int, obj: ScrapLotHold) -> LotHoldDetail:
        hold = await db.scalar(select(LotQualityHold).where(
            LotQualityHold.id == hold_id, LotQualityHold.deleted == 0
        ).with_for_update())
        if not hold:
            raise errors.NotFoundError(msg='LOT_HOLD_NOT_FOUND')
        if hold.status == LotHoldStatus.SCRAPPED:
            return LotHoldDetail.model_validate(hold)
        if hold.status not in ACTIVE_HOLD_STATUSES:
            raise errors.ConflictError(msg='LOT_HOLD_NOT_SCRAPPABLE')
        lot = await db.scalar(select(MaterialLot).where(
            MaterialLot.id == hold.lot_id, MaterialLot.deleted == 0
        ).with_for_update())
        balances = (await db.scalars(select(InventoryBalance).where(
            InventoryBalance.lot_id == lot.id,
            InventoryBalance.quantity > 0,
            InventoryBalance.deleted == 0,
        ).with_for_update())).all()
        from backend.plugin.inventory.enums import StockTransactionType
        from backend.plugin.inventory.service.inventory_service import inventory_service

        for balance in balances:
            await inventory_service.post_transaction(
                db,
                idempotency_key=f'LOT_HOLD_SCRAP:{hold.id}:{balance.id}',
                transaction_type=StockTransactionType.SCRAP,
                material_id=balance.material_id,
                lot_id=balance.lot_id,
                warehouse_id=balance.warehouse_id,
                location_id=balance.location_id,
                quantity_delta=-balance.quantity,
                reference_type='LOT_QUALITY_HOLD',
                reference_id=hold.id,
                reference_no=hold.hold_no,
                remark=obj.decision_reason,
                operator_id=ShelfLifeService._operator_id(),
            )
        lot.status = LotStatus.CLOSED
        lot.quality_status = QualityStatus.FAIL
        hold.status = LotHoldStatus.SCRAPPED
        hold.decided_at = timezone.now()
        hold.decided_by = ShelfLifeService._operator_id()
        hold.decision_reason = obj.decision_reason
        alert = await db.scalar(select(LotExpiryAlert).where(
            LotExpiryAlert.lot_id == lot.id, LotExpiryAlert.deleted == 0
        ).with_for_update())
        if alert:
            alert.status = ExpiryAlertStatus.CLOSED
            alert.resolved_at = timezone.now()
        await db.flush()
        return LotHoldDetail.model_validate(hold)

    @staticmethod
    async def _downstream_lot_ids(db: AsyncSession, root_lot_id: int) -> set[int]:
        found = {root_lot_id}
        queue = deque([root_lot_id])
        while queue:
            source_id = queue.popleft()
            target_ids = (await db.scalars(select(TraceRelation.target_id).where(
                TraceRelation.source_type == TraceObjectType.LOT,
                TraceRelation.source_id == source_id,
                TraceRelation.target_type == TraceObjectType.LOT,
            ))).all()
            for target_id in target_ids:
                if target_id not in found:
                    found.add(target_id)
                    queue.append(target_id)
        return found

    @staticmethod
    async def recall_detail(db: AsyncSession, recall: LotRecall) -> LotRecallDetail:
        items = (await db.scalars(select(LotRecallItem).where(
            LotRecallItem.recall_id == recall.id,
            LotRecallItem.deleted == 0,
        ).order_by(LotRecallItem.item_type, LotRecallItem.id))).all()
        detail = LotRecallDetail.model_validate(recall)
        detail.items = [RecallItemDetail.model_validate(item) for item in items]
        return detail

    @staticmethod
    async def create_recall(db: AsyncSession, obj: CreateLotRecall) -> LotRecallDetail:
        root = await db.scalar(select(MaterialLot).where(
            MaterialLot.id == obj.root_lot_id, MaterialLot.deleted == 0
        ).with_for_update())
        if not root:
            raise errors.NotFoundError(msg='LOT_NOT_FOUND')
        active = await db.scalar(select(LotRecall.id).where(
            LotRecall.root_lot_id == root.id,
            LotRecall.status == LotRecallStatus.ACTIVE,
            LotRecall.deleted == 0,
        ))
        if active:
            raise errors.ConflictError(msg='ACTIVE_LOT_RECALL_EXISTS')
        number = (obj.recall_no or f'RECALL-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        recall = LotRecall(
            recall_no=number,
            root_lot_id=root.id,
            reason=obj.reason,
            severity=obj.severity.upper(),
            initiated_at=timezone.now(),
            initiated_by=ShelfLifeService._operator_id(),
        )
        db.add(recall)
        await db.flush()
        lot_ids = await ShelfLifeService._downstream_lot_ids(db, root.id)
        inventory_rows = (await db.execute(select(
            InventoryBalance.lot_id,
            func.sum(InventoryBalance.quantity),
        ).where(
            InventoryBalance.lot_id.in_(lot_ids),
            InventoryBalance.quantity > 0,
            InventoryBalance.deleted == 0,
        ).group_by(InventoryBalance.lot_id))).all()
        for lot_id, quantity in inventory_rows:
            lot = await db.scalar(select(MaterialLot).where(
                MaterialLot.id == lot_id, MaterialLot.deleted == 0
            ).with_for_update())
            await ShelfLifeService._ensure_hold(
                db,
                lot,
                reason=LotHoldReason.RECALL,
                source_type='LOT_RECALL',
                source_id=recall.id,
                source_no=recall.recall_no,
            )
            db.add(LotRecallItem(
                recall_id=recall.id,
                item_key=f'LOT:{lot_id}',
                item_type=RecallItemType.INVENTORY_LOT,
                status=RecallItemStatus.QUARANTINED,
                lot_id=lot_id,
                quantity=Decimal(quantity or 0),
            ))
        shipment_rows = (await db.execute(
            select(ShipmentLine, Shipment)
            .join(Shipment, Shipment.id == ShipmentLine.shipment_id)
            .where(
                ShipmentLine.lot_id.in_(lot_ids),
                ShipmentLine.deleted == 0,
                Shipment.deleted == 0,
            )
        )).all()
        for line, shipment in shipment_rows:
            db.add(LotRecallItem(
                recall_id=recall.id,
                item_key=f'SHIPMENT_LINE:{line.id}',
                item_type=RecallItemType.SHIPMENT,
                status=RecallItemStatus.PENDING,
                lot_id=line.lot_id,
                shipment_id=shipment.id,
                shipment_line_id=line.id,
                customer_id=shipment.customer_id,
                quantity=line.quantity,
            ))
        await db.flush()
        return await ShelfLifeService.recall_detail(db, recall)

    @staticmethod
    async def list_recalls(db: AsyncSession, status: str | None = None) -> list[LotRecallDetail]:
        statement = select(LotRecall).where(LotRecall.deleted == 0)
        if status:
            statement = statement.where(LotRecall.status == status)
        rows = (await db.scalars(statement.order_by(LotRecall.initiated_at.desc()))).all()
        return [await ShelfLifeService.recall_detail(db, row) for row in rows]

    @staticmethod
    async def get_recall(db: AsyncSession, recall_id: int) -> LotRecallDetail:
        recall = await db.scalar(select(LotRecall).where(
            LotRecall.id == recall_id, LotRecall.deleted == 0
        ))
        if not recall:
            raise errors.NotFoundError(msg='LOT_RECALL_NOT_FOUND')
        return await ShelfLifeService.recall_detail(db, recall)

    @staticmethod
    async def update_recall_item(
        db: AsyncSession, recall_id: int, item_id: int, obj: UpdateRecallItem
    ) -> RecallItemDetail:
        recall = await db.scalar(select(LotRecall).where(
            LotRecall.id == recall_id, LotRecall.deleted == 0
        ).with_for_update())
        if not recall:
            raise errors.NotFoundError(msg='LOT_RECALL_NOT_FOUND')
        if recall.status != LotRecallStatus.ACTIVE:
            raise errors.ConflictError(msg='LOT_RECALL_NOT_ACTIVE')
        item = await db.scalar(select(LotRecallItem).where(
            LotRecallItem.id == item_id,
            LotRecallItem.recall_id == recall.id,
            LotRecallItem.deleted == 0,
        ).with_for_update())
        if not item:
            raise errors.NotFoundError(msg='LOT_RECALL_ITEM_NOT_FOUND')
        item.status = obj.status
        item.action_notes = obj.action_notes
        item.handled_at = timezone.now()
        item.handled_by = ShelfLifeService._operator_id()
        await db.flush()
        return RecallItemDetail.model_validate(item)

    @staticmethod
    async def close_recall(db: AsyncSession, recall_id: int) -> LotRecallDetail:
        recall = await db.scalar(select(LotRecall).where(
            LotRecall.id == recall_id, LotRecall.deleted == 0
        ).with_for_update())
        if not recall:
            raise errors.NotFoundError(msg='LOT_RECALL_NOT_FOUND')
        if recall.status == LotRecallStatus.CLOSED:
            return await ShelfLifeService.recall_detail(db, recall)
        if recall.status != LotRecallStatus.ACTIVE:
            raise errors.ConflictError(msg='LOT_RECALL_NOT_ACTIVE')
        items = (await db.scalars(select(LotRecallItem).where(
            LotRecallItem.recall_id == recall.id,
            LotRecallItem.deleted == 0,
        ).with_for_update())).all()
        if any(item.status not in (RecallItemStatus.RETURNED, RecallItemStatus.CLOSED) for item in items):
            raise errors.ConflictError(msg='LOT_RECALL_ITEMS_NOT_RESOLVED')
        holds = (await db.scalars(select(LotQualityHold).where(
            LotQualityHold.reason == LotHoldReason.RECALL,
            LotQualityHold.source_id == recall.id,
            LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
            LotQualityHold.deleted == 0,
        ).with_for_update())).all()
        now = timezone.now()
        for hold in holds:
            hold.status = LotHoldStatus.RELEASED
            hold.decided_at = now
            hold.decided_by = ShelfLifeService._operator_id()
            hold.decision_reason = '召回处置完成'
            lot = await db.scalar(select(MaterialLot).where(
                MaterialLot.id == hold.lot_id, MaterialLot.deleted == 0
            ).with_for_update())
            other_hold = await db.scalar(select(LotQualityHold.id).where(
                LotQualityHold.lot_id == lot.id,
                LotQualityHold.id != hold.id,
                LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
                LotQualityHold.deleted == 0,
            ))
            if not other_hold and (lot.expiry_date is None or lot.expiry_date > now):
                previous_lot_status = (hold.previous_lot_status or LotStatus.ACTIVE.value).rsplit('.', 1)[-1]
                previous_quality_status = (
                    hold.previous_quality_status or QualityStatus.PASS.value
                ).rsplit('.', 1)[-1]
                lot.status = LotStatus(previous_lot_status)
                lot.quality_status = QualityStatus(previous_quality_status)
        recall.status = LotRecallStatus.CLOSED
        recall.closed_at = now
        recall.closed_by = ShelfLifeService._operator_id()
        await db.flush()
        return await ShelfLifeService.recall_detail(db, recall)

    @staticmethod
    async def dashboard(db: AsyncSession) -> ShelfLifeDashboard:
        counts = dict((await db.execute(select(
            LotExpiryAlert.level, func.count(LotExpiryAlert.id)
        ).where(
            LotExpiryAlert.status != ExpiryAlertStatus.CLOSED,
            LotExpiryAlert.deleted == 0,
        ).group_by(LotExpiryAlert.level))).all())
        return ShelfLifeDashboard(
            policy_count=int(await db.scalar(select(func.count(ShelfLifePolicy.id)).where(
                ShelfLifePolicy.status == ShelfLifePolicyStatus.ACTIVE,
                ShelfLifePolicy.deleted == 0,
            )) or 0),
            warning_count=int(counts.get(ExpiryAlertLevel.WARNING, 0)),
            critical_count=int(counts.get(ExpiryAlertLevel.CRITICAL, 0)),
            expired_count=int(counts.get(ExpiryAlertLevel.EXPIRED, 0)),
            open_hold_count=int(await db.scalar(select(func.count(LotQualityHold.id)).where(
                LotQualityHold.status.in_(ACTIVE_HOLD_STATUSES),
                LotQualityHold.deleted == 0,
            )) or 0),
            active_recall_count=int(await db.scalar(select(func.count(LotRecall.id)).where(
                LotRecall.status == LotRecallStatus.ACTIVE,
                LotRecall.deleted == 0,
            )) or 0),
        )


shelf_life_service = ShelfLifeService()
