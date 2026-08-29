from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom
from backend.plugin.inventory.enums import (
    InventoryPolicyStatus,
    ReplenishmentAlertLevel,
    ReplenishmentOrderType,
    ReplenishmentStatus,
)
from backend.plugin.inventory.model import InventoryBalance, InventoryPolicy, ReplenishmentSuggestion
from backend.plugin.inventory.schema.inventory import (
    GenerateReplenishment,
    InventoryPolicyDetail,
    InventoryPolicyUpsert,
    ReleaseReplenishment,
    ReplenishmentDashboard,
    ReplenishmentSuggestionDetail,
)
from backend.plugin.material.enums import MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.planning.model import PlannedOrder
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import WorkOrder
from backend.plugin.production.schema.production import CreateWorkOrder
from backend.plugin.production.service import production_service
from backend.plugin.purchasing.enums import PurchaseOrderStatus
from backend.plugin.purchasing.model import PurchaseOrder, PurchaseOrderLine
from backend.plugin.purchasing.schema.purchasing import CreatePurchaseOrder, CreatePurchaseOrderLine
from backend.plugin.purchasing.service import purchasing_service
from backend.plugin.routing.enums import RoutingStatus
from backend.plugin.routing.model import Routing
from backend.plugin.sales.enums import SalesOrderStatus
from backend.plugin.sales.model import SalesOrder, SalesOrderLine
from backend.plugin.sales.service import promise_service
from backend.utils.timezone import timezone

ZERO = Decimal('0')


class ReplenishmentService:
    @staticmethod
    async def list_policies(db: AsyncSession) -> list[InventoryPolicyDetail]:
        rows = (
            await db.scalars(
                select(InventoryPolicy)
                .where(InventoryPolicy.deleted == 0)
                .order_by(InventoryPolicy.material_id)
            )
        ).all()
        return [InventoryPolicyDetail.model_validate(row) for row in rows]

    @staticmethod
    async def upsert_policy(
        db: AsyncSession, material_id: int, obj: InventoryPolicyUpsert
    ) -> InventoryPolicyDetail:
        material = await db.scalar(
            select(Material).where(
                Material.id == material_id,
                Material.deleted == 0,
                Material.status == MaterialStatus.ACTIVE,
            )
        )
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if obj.reorder_point < obj.safety_stock:
            raise errors.RequestError(msg='REORDER_POINT_BELOW_SAFETY_STOCK')
        if obj.max_stock and obj.max_stock < obj.reorder_point:
            raise errors.RequestError(msg='MAX_STOCK_BELOW_REORDER_POINT')
        policy = await db.scalar(
            select(InventoryPolicy)
            .where(InventoryPolicy.material_id == material_id, InventoryPolicy.deleted == 0)
            .with_for_update()
        )
        values = obj.model_dump()
        if policy:
            for key, value in values.items():
                setattr(policy, key, value)
        else:
            policy = InventoryPolicy(material_id=material_id, **values)
            db.add(policy)
        await db.flush()
        return InventoryPolicyDetail.model_validate(policy)

    @staticmethod
    async def _supply_and_demand(
        db: AsyncSession, material_id: int
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        balances = (
            await db.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.material_id == material_id,
                    InventoryBalance.deleted == 0,
                )
            )
        ).all()
        on_hand = sum((row.quantity or ZERO for row in balances), ZERO)
        reserved = sum((row.reserved_quantity or ZERO for row in balances), ZERO)
        purchase_rows = (
            await db.execute(
                select(PurchaseOrderLine.ordered_quantity, PurchaseOrderLine.received_quantity)
                .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.purchase_order_id)
                .where(
                    PurchaseOrderLine.material_id == material_id,
                    PurchaseOrderLine.deleted == 0,
                    PurchaseOrder.deleted == 0,
                    PurchaseOrder.status.in_(
                        [
                            PurchaseOrderStatus.DRAFT,
                            PurchaseOrderStatus.CONFIRMED,
                            PurchaseOrderStatus.PARTIALLY_RECEIVED,
                        ]
                    ),
                )
            )
        ).all()
        open_purchase = sum(
            (
                max((ordered or ZERO) - (received or ZERO), ZERO)
                for ordered, received in purchase_rows
            ),
            ZERO,
        )
        work_orders = (
            await db.scalars(
                select(WorkOrder).where(
                    WorkOrder.product_material_id == material_id,
                    WorkOrder.deleted == 0,
                    WorkOrder.status.in_(
                        [
                            WorkOrderStatus.DRAFT,
                            WorkOrderStatus.RELEASED,
                            WorkOrderStatus.IN_PROGRESS,
                        ]
                    ),
                )
            )
        ).all()
        open_production = sum(
            (
                max((row.planned_quantity or ZERO) - (row.completed_quantity or ZERO), ZERO)
                for row in work_orders
            ),
            ZERO,
        )
        demand_rows = (
            await db.execute(
                select(SalesOrderLine.ordered_quantity, SalesOrderLine.shipped_quantity)
                .join(SalesOrder, SalesOrder.id == SalesOrderLine.sales_order_id)
                .where(
                    SalesOrderLine.material_id == material_id,
                    SalesOrderLine.deleted == 0,
                    SalesOrder.deleted == 0,
                    SalesOrder.status.in_(
                        [SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_SHIPPED]
                    ),
                )
            )
        ).all()
        demand = sum(
            (
                max((ordered or ZERO) - (shipped or ZERO), ZERO)
                for ordered, shipped in demand_rows
            ),
            ZERO,
        )
        return on_hand, reserved, open_purchase, open_production, demand

    @staticmethod
    async def generate(
        db: AsyncSession, obj: GenerateReplenishment
    ) -> list[ReplenishmentSuggestionDetail]:
        statement = select(InventoryPolicy).where(
            InventoryPolicy.deleted == 0,
            InventoryPolicy.status == InventoryPolicyStatus.ACTIVE,
        )
        if obj.material_ids:
            statement = statement.where(InventoryPolicy.material_id.in_(obj.material_ids))
        statement = statement.with_for_update()
        policies = (await db.scalars(statement.order_by(InventoryPolicy.material_id))).all()
        result: list[ReplenishmentSuggestionDetail] = []
        evaluated_at = timezone.now()
        for policy in policies:
            material = await db.scalar(
                select(Material).where(Material.id == policy.material_id, Material.deleted == 0)
            )
            if not material or material.status != MaterialStatus.ACTIVE:
                continue
            unit = await db.scalar(
                select(UnitOfMeasure).where(
                    UnitOfMeasure.id == material.base_unit_id,
                    UnitOfMeasure.deleted == 0,
                    UnitOfMeasure.status == UnitStatus.ACTIVE,
                )
            )
            if not unit or not (material.purchasable or material.producible):
                continue
            on_hand, reserved, purchase, production, demand = await ReplenishmentService._supply_and_demand(
                db, material.id
            )
            projected = on_hand - reserved + purchase + production - demand
            if projected < policy.safety_stock:
                alert = ReplenishmentAlertLevel.SHORTAGE
            elif projected < policy.reorder_point:
                alert = ReplenishmentAlertLevel.REORDER
            else:
                alert = ReplenishmentAlertLevel.COVERED
            target = max(policy.max_stock, policy.reorder_point, policy.safety_stock)
            quantity = max(target - projected, ZERO)
            if quantity > ZERO and policy.min_order_quantity > quantity:
                quantity = policy.min_order_quantity
            order_type = (
                ReplenishmentOrderType.PURCHASE
                if material.purchasable and not material.producible
                else ReplenishmentOrderType.PRODUCTION
                if material.producible
                else ReplenishmentOrderType.PURCHASE
            )
            active_suggestions = list((await db.scalars(
                select(ReplenishmentSuggestion)
                .where(
                    ReplenishmentSuggestion.material_id == material.id,
                    ReplenishmentSuggestion.status.in_(
                        (ReplenishmentStatus.SUGGESTED, ReplenishmentStatus.FIRM)
                    ),
                    ReplenishmentSuggestion.deleted == 0,
                )
                .order_by(ReplenishmentSuggestion.id.desc())
                .with_for_update()
            )).all())
            firm = next(
                (row for row in active_suggestions if row.status == ReplenishmentStatus.FIRM),
                None,
            )
            suggested_rows = [
                row for row in active_suggestions if row.status == ReplenishmentStatus.SUGGESTED
            ]
            existing = suggested_rows[0] if suggested_rows else None
            for duplicate in suggested_rows[1:]:
                duplicate.status = ReplenishmentStatus.CANCELLED
            if alert == ReplenishmentAlertLevel.COVERED:
                for row in suggested_rows:
                    row.status = ReplenishmentStatus.CANCELLED
                if suggested_rows:
                    await db.flush()
                continue
            if firm:
                for row in suggested_rows:
                    row.status = ReplenishmentStatus.CANCELLED
                await db.flush()
                result.append(ReplenishmentSuggestionDetail.model_validate(firm))
                continue
            values = dict(
                material_id=material.id,
                policy_id=policy.id,
                evaluated_at=evaluated_at,
                due_date=(evaluated_at.date() + timedelta(days=policy.purchase_lead_days if order_type == ReplenishmentOrderType.PURCHASE else policy.production_lead_days)),
                material_code_snapshot=material.material_code,
                material_name_snapshot=material.material_name,
                unit_code_snapshot=unit.unit_code,
                on_hand_quantity=on_hand,
                reserved_quantity=reserved,
                open_purchase_quantity=purchase,
                open_production_quantity=production,
                demand_quantity=demand,
                projected_available_quantity=projected,
                safety_stock=policy.safety_stock,
                reorder_point=policy.reorder_point,
                suggested_quantity=quantity,
                order_type=order_type,
                alert_level=alert,
            )
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
                suggestion = existing
            else:
                suggestion = ReplenishmentSuggestion(
                    suggestion_no=f'REP-{evaluated_at:%Y%m%d%H%M%S}-{material.id}-{uuid4().hex[:4]}'.upper(),
                    status=ReplenishmentStatus.SUGGESTED,
                    **values,
                )
                db.add(suggestion)
            await db.flush()
            result.append(ReplenishmentSuggestionDetail.model_validate(suggestion))
        return result

    @staticmethod
    async def list_suggestions(
        db: AsyncSession, status: str | None = None
    ) -> list[ReplenishmentSuggestionDetail]:
        statement = select(ReplenishmentSuggestion).where(ReplenishmentSuggestion.deleted == 0)
        if status:
            statement = statement.where(ReplenishmentSuggestion.status == status)
        rows = (
            await db.scalars(statement.order_by(ReplenishmentSuggestion.evaluated_at.desc()))
        ).all()
        return [ReplenishmentSuggestionDetail.model_validate(row) for row in rows]

    @staticmethod
    async def firm(
        db: AsyncSession, suggestion_id: int
    ) -> ReplenishmentSuggestionDetail:
        suggestion = await db.scalar(
            select(ReplenishmentSuggestion)
            .where(ReplenishmentSuggestion.id == suggestion_id, ReplenishmentSuggestion.deleted == 0)
            .with_for_update()
        )
        if not suggestion:
            raise errors.NotFoundError(msg='REPLENISHMENT_SUGGESTION_NOT_FOUND')
        if suggestion.status == ReplenishmentStatus.FIRM:
            return ReplenishmentSuggestionDetail.model_validate(suggestion)
        if suggestion.status != ReplenishmentStatus.SUGGESTED:
            raise errors.ConflictError(msg='REPLENISHMENT_SUGGESTION_NOT_FIRMABLE')
        suggestion.status = ReplenishmentStatus.FIRM
        await db.flush()
        return ReplenishmentSuggestionDetail.model_validate(suggestion)

    @staticmethod
    async def release(
        db: AsyncSession, suggestion_id: int, obj: ReleaseReplenishment
    ) -> ReplenishmentSuggestionDetail:
        suggestion = await db.scalar(
            select(ReplenishmentSuggestion)
            .where(ReplenishmentSuggestion.id == suggestion_id, ReplenishmentSuggestion.deleted == 0)
            .with_for_update()
        )
        if not suggestion:
            raise errors.NotFoundError(msg='REPLENISHMENT_SUGGESTION_NOT_FOUND')
        if suggestion.status not in (ReplenishmentStatus.SUGGESTED, ReplenishmentStatus.FIRM):
            raise errors.ConflictError(msg='REPLENISHMENT_SUGGESTION_NOT_RELEASABLE')
        material = await db.scalar(
            select(Material).where(Material.id == suggestion.material_id, Material.deleted == 0)
        )
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if suggestion.order_type == ReplenishmentOrderType.PURCHASE:
            if not obj.supplier_id:
                raise errors.RequestError(msg='SUPPLIER_REQUIRED_FOR_REPLENISHMENT')
            document = await purchasing_service.create_order(
                db,
                CreatePurchaseOrder(
                    supplier_id=obj.supplier_id,
                    currency=obj.currency,
                    remark=obj.remark or f'Released from {suggestion.suggestion_no}',
                    lines=[
                        CreatePurchaseOrderLine(
                            material_id=suggestion.material_id,
                            ordered_quantity=suggestion.suggested_quantity,
                            unit_price=obj.unit_price,
                            requested_delivery_at=datetime.combine(
                                suggestion.due_date, time.min, tzinfo=timezone.tz_info
                            ),
                        )
                    ],
                ),
            )
            source_type, source_id, source_no = 'PURCHASE_ORDER', document.id, document.purchase_order_no
        else:
            bom = await db.scalar(
                select(Bom).where(
                    Bom.product_material_id == suggestion.material_id,
                    Bom.status == BomStatus.ACTIVE,
                    Bom.deleted == 0,
                )
            )
            if not bom:
                raise errors.ConflictError(msg='ACTIVE_BOM_REQUIRED_FOR_REPLENISHMENT')
            routing_statement = select(Routing).where(
                Routing.product_material_id == suggestion.material_id,
                Routing.status == RoutingStatus.ACTIVE,
                Routing.deleted == 0,
            )
            if obj.routing_id:
                routing_statement = routing_statement.where(Routing.id == obj.routing_id)
            routing = await db.scalar(
                routing_statement.order_by(Routing.is_default.desc(), Routing.id.desc())
            )
            if not routing:
                raise errors.ConflictError(msg='ACTIVE_ROUTING_REQUIRED_FOR_REPLENISHMENT')
            document = await production_service.create_order(
                db,
                CreateWorkOrder(
                    product_material_id=suggestion.material_id,
                    bom_id=bom.id,
                    routing_id=routing.id,
                    planned_quantity=suggestion.suggested_quantity,
                    planned_start_at=datetime.combine(
                        suggestion.due_date, time.min, tzinfo=timezone.tz_info
                    ),
                    planned_end_at=datetime.combine(
                        suggestion.due_date, time.min, tzinfo=timezone.tz_info
                    ),
                    remark=obj.remark or f'Released from {suggestion.suggestion_no}',
                ),
            )
            source_type, source_id, source_no = 'WORK_ORDER', document.id, document.work_order_no
        suggestion.status = ReplenishmentStatus.RELEASED
        suggestion.source_document_type = source_type
        suggestion.source_document_id = source_id
        suggestion.source_document_no = source_no
        suggestion.released_at = timezone.now()
        await db.flush()
        await promise_service.recalculate_open_orders(db)
        return ReplenishmentSuggestionDetail.model_validate(suggestion)

    @staticmethod
    async def dashboard(db: AsyncSession) -> ReplenishmentDashboard:
        policies = (
            await db.scalars(
                select(InventoryPolicy).where(
                    InventoryPolicy.deleted == 0,
                    InventoryPolicy.status == InventoryPolicyStatus.ACTIVE,
                )
            )
        ).all()
        suggestions = (
            await db.scalars(
                select(ReplenishmentSuggestion).where(
                    ReplenishmentSuggestion.deleted == 0,
                    ReplenishmentSuggestion.status.in_(
                        [ReplenishmentStatus.SUGGESTED, ReplenishmentStatus.FIRM]
                    ),
                )
            )
        ).all()
        return ReplenishmentDashboard(
            policy_count=len(policies),
            suggestion_count=len(suggestions),
            shortage_count=sum(row.alert_level == ReplenishmentAlertLevel.SHORTAGE for row in suggestions),
            reorder_count=sum(row.alert_level == ReplenishmentAlertLevel.REORDER for row in suggestions),
            total_suggested_quantity=sum((row.suggested_quantity for row in suggestions), ZERO),
            total_demand_quantity=sum((row.demand_quantity for row in suggestions), ZERO),
            purchase_suggestion_count=sum(row.order_type == ReplenishmentOrderType.PURCHASE for row in suggestions),
            production_suggestion_count=sum(row.order_type == ReplenishmentOrderType.PRODUCTION for row in suggestions),
        )


replenishment_service = ReplenishmentService()
