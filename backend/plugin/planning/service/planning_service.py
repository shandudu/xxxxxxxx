from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom, BomItem
from backend.plugin.inventory.model import InventoryBalance
from backend.plugin.material.enums import MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.planning.crud import planning_repo
from backend.plugin.planning.enums import (
    MpsDemandType,
    MpsPlanStatus,
    MrpRunStatus,
    PlannedOrderStatus,
    PlannedOrderType,
)
from backend.plugin.planning.model import MpsDemand, MpsPlan, MrpRequirement, MrpRun, PlannedOrder
from backend.plugin.planning.schema.planning import (
    CreateMpsDemand,
    CreateMpsPlan,
    CreateMrpRun,
    ImportSalesOrderDemand,
    MpsDemandDetail,
    MpsPlanDetail,
    MrpRequirementDetail,
    MrpRunDetail,
    PlannedOrderDetail,
    ReleasePlannedOrder,
)
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
from backend.plugin.sales.service.promise_service import promise_service
from backend.utils.timezone import timezone

ZERO = Decimal('0')


@dataclass
class SupplyBucket:
    on_hand: Decimal = ZERO
    open_purchase: Decimal = ZERO
    open_production: Decimal = ZERO


def allocate_supply(gross_requirement: Decimal, supply: SupplyBucket) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Allocate supply in deterministic priority order and mutate the remaining bucket."""
    remaining = gross_requirement
    on_hand = min(remaining, supply.on_hand)
    supply.on_hand -= on_hand
    remaining -= on_hand
    purchase = min(remaining, supply.open_purchase)
    supply.open_purchase -= purchase
    remaining -= purchase
    production = min(remaining, supply.open_production)
    supply.open_production -= production
    remaining -= production
    return on_hand, purchase, production, remaining


class _MrpCalculator:
    def __init__(self, db: AsyncSession, run: MrpRun) -> None:
        self.db = db
        self.run = run
        self.requirement_sequence = 0
        self.order_sequence = 0
        self.supply: dict[int, SupplyBucket] = {}
        self.materials: dict[int, Material] = {}
        self.units: dict[int, UnitOfMeasure] = {}

    async def _material(self, material_id: int) -> Material:
        if material_id not in self.materials:
            material = await self.db.scalar(
                select(Material).where(Material.id == material_id, Material.deleted == 0)
            )
            if not material or material.status != MaterialStatus.ACTIVE:
                raise errors.ConflictError(msg=f'MRP_MATERIAL_UNAVAILABLE:{material_id}')
            self.materials[material_id] = material
        return self.materials[material_id]

    async def _unit(self, unit_id: int) -> UnitOfMeasure:
        if unit_id not in self.units:
            unit = await self.db.scalar(
                select(UnitOfMeasure).where(UnitOfMeasure.id == unit_id, UnitOfMeasure.deleted == 0)
            )
            if not unit or unit.status != UnitStatus.ACTIVE:
                raise errors.ConflictError(msg=f'MRP_UNIT_UNAVAILABLE:{unit_id}')
            self.units[unit_id] = unit
        return self.units[unit_id]

    async def _supply(self, material_id: int) -> SupplyBucket:
        if material_id in self.supply:
            return self.supply[material_id]

        on_hand = ZERO
        if self.run.include_inventory:
            on_hand = await self.db.scalar(
                select(
                    func.coalesce(
                        func.sum(InventoryBalance.quantity - InventoryBalance.reserved_quantity),
                        ZERO,
                    )
                ).where(InventoryBalance.material_id == material_id, InventoryBalance.deleted == 0)
            ) or ZERO

        open_purchase = ZERO
        if self.run.include_open_purchase:
            open_purchase = await self.db.scalar(
                select(
                    func.coalesce(
                        func.sum(PurchaseOrderLine.ordered_quantity - PurchaseOrderLine.received_quantity),
                        ZERO,
                    )
                )
                .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.purchase_order_id)
                .where(
                    PurchaseOrderLine.material_id == material_id,
                    PurchaseOrderLine.deleted == 0,
                    PurchaseOrder.deleted == 0,
                    PurchaseOrder.status.in_(
                        [PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED]
                    ),
                )
            ) or ZERO

        open_production = ZERO
        if self.run.include_open_production:
            open_production = await self.db.scalar(
                select(
                    func.coalesce(
                        func.sum(WorkOrder.planned_quantity - WorkOrder.completed_quantity),
                        ZERO,
                    )
                ).where(
                    WorkOrder.product_material_id == material_id,
                    WorkOrder.deleted == 0,
                    WorkOrder.status.in_(
                        [WorkOrderStatus.DRAFT, WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS]
                    ),
                )
            ) or ZERO

        bucket = SupplyBucket(
            on_hand=Decimal(on_hand),
            open_purchase=Decimal(open_purchase),
            open_production=Decimal(open_production),
        )
        self.supply[material_id] = bucket
        return bucket

    async def _active_bom(self, material_id: int, requirement_date: date) -> Bom | None:
        candidates = (
            await self.db.scalars(
                select(Bom)
                .where(
                    Bom.product_material_id == material_id,
                    Bom.status == BomStatus.ACTIVE,
                    Bom.deleted == 0,
                )
                .order_by(Bom.is_default.desc(), Bom.effective_from.desc(), Bom.id.desc())
            )
        ).all()
        for bom in candidates:
            effective_from = bom.effective_from.date() if bom.effective_from else None
            effective_to = bom.effective_to.date() if bom.effective_to else None
            if effective_from and requirement_date < effective_from:
                continue
            if effective_to and requirement_date > effective_to:
                continue
            return bom
        return None

    async def process(
        self,
        *,
        demand: MpsDemand,
        material_id: int,
        gross_requirement: Decimal,
        requirement_date: date,
        level_no: int,
        path: tuple[int, ...] = (),
        path_codes: tuple[str, ...] = (),
        parent_material_id: int | None = None,
        source_bom_id: int | None = None,
        source_bom_item_id: int | None = None,
    ) -> None:
        if level_no > self.run.max_level:
            raise errors.ConflictError(msg=f'MRP_MAX_LEVEL_EXCEEDED:{self.run.max_level}')
        if material_id in path:
            raise errors.ConflictError(msg=f'BOM_CYCLE_DETECTED:{material_id}')

        material = await self._material(material_id)
        unit = await self._unit(material.base_unit_id)
        on_hand, purchase, production, net = allocate_supply(
            gross_requirement, await self._supply(material.id)
        )

        active_bom: Bom | None = None
        order_type: PlannedOrderType | None = None
        if net > ZERO and material.producible:
            active_bom = await self._active_bom(material.id, requirement_date)
            if active_bom:
                order_type = PlannedOrderType.PRODUCTION
        if net > ZERO and order_type is None and material.purchasable:
            order_type = PlannedOrderType.PURCHASE

        planned_quantity = net if order_type else ZERO
        uncovered_quantity = net if order_type is None else ZERO
        self.requirement_sequence += 1
        current_path_codes = (*path_codes, material.material_code)
        requirement = MrpRequirement(
            mrp_run_id=self.run.id,
            sequence_no=self.requirement_sequence,
            mps_demand_id=demand.id,
            level_no=level_no,
            material_id=material.id,
            requirement_date=requirement_date,
            gross_requirement=gross_requirement,
            material_code_snapshot=material.material_code,
            material_name_snapshot=material.material_name,
            unit_code_snapshot=unit.unit_code,
            source_path=' > '.join(current_path_codes)[:500],
            parent_material_id=parent_material_id,
            bom_id=source_bom_id,
            bom_item_id=source_bom_item_id,
            on_hand_allocated=on_hand,
            purchase_supply_allocated=purchase,
            production_supply_allocated=production,
            net_requirement=net,
            planned_order_quantity=planned_quantity,
            uncovered_quantity=uncovered_quantity,
        )
        self.db.add(requirement)
        await self.db.flush()

        if not order_type:
            return

        lead_days = (
            self.run.default_production_lead_days
            if order_type == PlannedOrderType.PRODUCTION
            else self.run.default_purchase_lead_days
        )
        self.order_sequence += 1
        planned_order = PlannedOrder(
            planned_order_no=(
                f'MPO-{self.run.id}-{self.order_sequence:05d}-{uuid4().hex[:4]}'
            ).upper(),
            mrp_run_id=self.run.id,
            mrp_requirement_id=requirement.id,
            sequence_no=self.order_sequence,
            material_id=material.id,
            order_type=order_type,
            quantity=planned_quantity,
            release_date=requirement_date - timedelta(days=lead_days),
            due_date=requirement_date,
            material_code_snapshot=material.material_code,
            material_name_snapshot=material.material_name,
            unit_code_snapshot=unit.unit_code,
            bom_id=active_bom.id if active_bom else None,
        )
        self.db.add(planned_order)
        await self.db.flush()

        if order_type != PlannedOrderType.PRODUCTION or not active_bom:
            return

        items = (
            await self.db.scalars(
                select(BomItem)
                .where(BomItem.bom_id == active_bom.id, BomItem.deleted == 0)
                .order_by(BomItem.line_no)
            )
        ).all()
        for item in items:
            if item.is_optional:
                continue
            base_required = item.quantity * planned_quantity / active_bom.base_quantity
            component_quantity = (
                base_required * (Decimal('1') + item.loss_rate / Decimal('100'))
                + item.fixed_loss_qty
            )
            if component_quantity <= ZERO:
                continue
            await self.process(
                demand=demand,
                material_id=item.component_material_id,
                gross_requirement=component_quantity,
                requirement_date=planned_order.release_date,
                level_no=level_no + 1,
                path=(*path, material.id),
                path_codes=current_path_codes,
                parent_material_id=material.id,
                source_bom_id=active_bom.id,
                source_bom_item_id=item.id,
            )


class PlanningService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _plan_detail(plan: MpsPlan, demands: Sequence[MpsDemand] = ()) -> MpsPlanDetail:
        detail = MpsPlanDetail.model_validate(plan)
        detail.demands = [MpsDemandDetail.model_validate(item) for item in demands]
        return detail

    @staticmethod
    def _run_detail(
        run: MrpRun,
        requirements: Sequence[MrpRequirement] = (),
        planned_orders: Sequence[PlannedOrder] = (),
    ) -> MrpRunDetail:
        detail = MrpRunDetail.model_validate(run)
        detail.requirements = [MrpRequirementDetail.model_validate(item) for item in requirements]
        detail.planned_orders = [PlannedOrderDetail.model_validate(item) for item in planned_orders]
        return detail

    @staticmethod
    async def list_plans(db: AsyncSession, status: str | None = None) -> list[MpsPlanDetail]:
        return [
            PlanningService._plan_detail(plan, await planning_repo.demands(db, plan.id))
            for plan in await planning_repo.list_plans(db, status)
        ]

    @staticmethod
    async def get_plan(db: AsyncSession, plan_id: int) -> MpsPlanDetail:
        plan = await planning_repo.get_plan(db, plan_id)
        if not plan:
            raise errors.NotFoundError(msg='MPS_PLAN_NOT_FOUND')
        return PlanningService._plan_detail(plan, await planning_repo.demands(db, plan.id))

    @staticmethod
    async def create_plan(db: AsyncSession, obj: CreateMpsPlan) -> MpsPlanDetail:
        plan_no = (obj.plan_no or f'MPS-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await planning_repo.get_plan_by_no(db, plan_no):
            raise errors.ConflictError(msg='MPS_PLAN_NO_EXISTS')
        plan = MpsPlan(plan_no=plan_no, **obj.model_dump(exclude={'plan_no'}))
        db.add(plan)
        await db.flush()
        return PlanningService._plan_detail(plan)

    @staticmethod
    async def _material_and_unit(db: AsyncSession, material_id: int) -> tuple[Material, UnitOfMeasure]:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if not material or material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='MPS_MATERIAL_UNAVAILABLE')
        unit = await db.scalar(
            select(UnitOfMeasure).where(
                UnitOfMeasure.id == material.base_unit_id,
                UnitOfMeasure.deleted == 0,
                UnitOfMeasure.status == UnitStatus.ACTIVE,
            )
        )
        if not unit:
            raise errors.ConflictError(msg='MPS_MATERIAL_UNIT_UNAVAILABLE')
        return material, unit

    @staticmethod
    async def _draft_plan(db: AsyncSession, plan_id: int) -> MpsPlan:
        plan = await planning_repo.get_plan(db, plan_id, lock=True)
        if not plan:
            raise errors.NotFoundError(msg='MPS_PLAN_NOT_FOUND')
        if plan.status != MpsPlanStatus.DRAFT:
            raise errors.ConflictError(msg='MPS_PLAN_NOT_DRAFT')
        return plan

    @staticmethod
    def _validate_demand_date(plan: MpsPlan, demand_date: date) -> None:
        if demand_date < plan.horizon_start or demand_date > plan.horizon_end:
            raise errors.RequestError(msg='MPS_DEMAND_OUTSIDE_HORIZON')

    @staticmethod
    async def _next_line_no(db: AsyncSession, plan_id: int) -> int:
        value = await db.scalar(
            select(func.coalesce(func.max(MpsDemand.line_no), 0)).where(
                MpsDemand.mps_plan_id == plan_id,
                MpsDemand.deleted == 0,
            )
        )
        return int(value or 0) + 1

    @staticmethod
    async def add_demand(
        db: AsyncSession,
        plan_id: int,
        obj: CreateMpsDemand,
    ) -> MpsDemandDetail:
        plan = await PlanningService._draft_plan(db, plan_id)
        PlanningService._validate_demand_date(plan, obj.demand_date)
        if obj.demand_type == MpsDemandType.SALES_ORDER:
            raise errors.RequestError(msg='USE_SALES_ORDER_IMPORT')
        material, unit = await PlanningService._material_and_unit(db, obj.material_id)
        demand = MpsDemand(
            mps_plan_id=plan.id,
            line_no=await PlanningService._next_line_no(db, plan.id),
            material_id=material.id,
            unit_id=unit.id,
            demand_date=obj.demand_date,
            quantity=obj.quantity,
            material_code_snapshot=material.material_code,
            material_name_snapshot=material.material_name,
            unit_code_snapshot=unit.unit_code,
            demand_type=obj.demand_type,
            remark=obj.remark,
        )
        db.add(demand)
        await db.flush()
        return MpsDemandDetail.model_validate(demand)

    @staticmethod
    async def import_sales_orders(
        db: AsyncSession,
        plan_id: int,
        obj: ImportSalesOrderDemand,
    ) -> list[MpsDemandDetail]:
        plan = await PlanningService._draft_plan(db, plan_id)
        PlanningService._validate_demand_date(plan, obj.demand_date)
        if len(obj.sales_order_ids) != len(set(obj.sales_order_ids)):
            raise errors.RequestError(msg='DUPLICATE_SALES_ORDER_ID')

        orders = (
            await db.scalars(
                select(SalesOrder).where(
                    SalesOrder.id.in_(obj.sales_order_ids),
                    SalesOrder.deleted == 0,
                    SalesOrder.status.in_(
                        [SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_SHIPPED]
                    ),
                )
            )
        ).all()
        if len(orders) != len(obj.sales_order_ids):
            raise errors.ConflictError(msg='SALES_ORDER_NOT_CONFIRMED_OR_NOT_FOUND')

        next_line = await PlanningService._next_line_no(db, plan.id)
        imported: list[MpsDemand] = []
        for order in orders:
            lines = (
                await db.scalars(
                    select(SalesOrderLine)
                    .where(SalesOrderLine.sales_order_id == order.id, SalesOrderLine.deleted == 0)
                    .order_by(SalesOrderLine.line_no)
                )
            ).all()
            for line in lines:
                remaining = line.ordered_quantity - line.shipped_quantity
                if remaining <= ZERO:
                    continue
                existing = await db.scalar(
                    select(MpsDemand.id).where(
                        MpsDemand.mps_plan_id == plan.id,
                        MpsDemand.demand_type == MpsDemandType.SALES_ORDER,
                        MpsDemand.source_id == line.id,
                        MpsDemand.deleted == 0,
                    )
                )
                if existing:
                    continue
                demand = MpsDemand(
                    mps_plan_id=plan.id,
                    line_no=next_line,
                    material_id=line.material_id,
                    unit_id=line.unit_id,
                    demand_date=obj.demand_date,
                    quantity=remaining,
                    material_code_snapshot=line.material_code_snapshot,
                    material_name_snapshot=line.material_name_snapshot,
                    unit_code_snapshot=line.unit_code_snapshot,
                    demand_type=MpsDemandType.SALES_ORDER,
                    source_id=line.id,
                    source_no=f'{order.sales_order_no}/{line.line_no}',
                )
                db.add(demand)
                imported.append(demand)
                next_line += 1
        await db.flush()
        return [MpsDemandDetail.model_validate(item) for item in imported]

    @staticmethod
    async def delete_demand(db: AsyncSession, plan_id: int, demand_id: int) -> None:
        plan = await PlanningService._draft_plan(db, plan_id)
        demand = await planning_repo.get_demand(db, demand_id, lock=True)
        if not demand or demand.mps_plan_id != plan.id:
            raise errors.NotFoundError(msg='MPS_DEMAND_NOT_FOUND')
        demand.deleted = demand.id
        demand.deleted_time = timezone.now()
        await db.flush()

    @staticmethod
    async def confirm_plan(db: AsyncSession, plan_id: int) -> MpsPlanDetail:
        plan = await planning_repo.get_plan(db, plan_id, lock=True)
        if not plan:
            raise errors.NotFoundError(msg='MPS_PLAN_NOT_FOUND')
        if plan.status == MpsPlanStatus.CONFIRMED:
            return await PlanningService.get_plan(db, plan.id)
        if plan.status != MpsPlanStatus.DRAFT:
            raise errors.ConflictError(msg='MPS_PLAN_NOT_DRAFT')
        demands = await planning_repo.demands(db, plan.id)
        if not demands:
            raise errors.ConflictError(msg='MPS_PLAN_HAS_NO_DEMAND')
        plan.status = MpsPlanStatus.CONFIRMED
        await db.flush()
        return PlanningService._plan_detail(plan, demands)

    @staticmethod
    async def list_runs(db: AsyncSession, plan_id: int | None = None) -> list[MrpRunDetail]:
        return [PlanningService._run_detail(run) for run in await planning_repo.list_runs(db, plan_id)]

    @staticmethod
    async def get_run(db: AsyncSession, run_id: int) -> MrpRunDetail:
        run = await planning_repo.get_run(db, run_id)
        if not run:
            raise errors.NotFoundError(msg='MRP_RUN_NOT_FOUND')
        return PlanningService._run_detail(
            run,
            await planning_repo.requirements(db, run.id),
            await planning_repo.planned_orders(db, run.id),
        )

    @staticmethod
    async def run_mrp(db: AsyncSession, obj: CreateMrpRun) -> MrpRunDetail:
        plan = await planning_repo.get_plan(db, obj.mps_plan_id, lock=True)
        if not plan:
            raise errors.NotFoundError(msg='MPS_PLAN_NOT_FOUND')
        if plan.status != MpsPlanStatus.CONFIRMED:
            raise errors.ConflictError(msg='MPS_PLAN_NOT_CONFIRMED')
        demands = await planning_repo.demands(db, plan.id)
        if not demands:
            raise errors.ConflictError(msg='MPS_PLAN_HAS_NO_DEMAND')

        run = MrpRun(
            run_no=f'MRP-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper(),
            **obj.model_dump(),
        )
        db.add(run)
        await db.flush()
        calculator = _MrpCalculator(db, run)
        try:
            for demand in demands:
                await calculator.process(
                    demand=demand,
                    material_id=demand.material_id,
                    gross_requirement=demand.quantity,
                    requirement_date=demand.demand_date,
                    level_no=0,
                )
            run.status = MrpRunStatus.COMPLETED
        except Exception as exc:  # Persist a diagnosable failed-run snapshot.
            run.status = MrpRunStatus.FAILED
            run.error_message = str(exc)[:2000]
        run.requirement_count = calculator.requirement_sequence
        run.planned_order_count = calculator.order_sequence
        run.completed_at = timezone.now()
        if run.status == MrpRunStatus.COMPLETED:
            try:
                refresh = await promise_service.recalculate_open_orders(db)
                run.promise_refresh_at = refresh.assessed_at
                run.promise_assessment_count = refresh.assessed_line_count
            except Exception as exc:
                run.error_message = f'{run.error_message or ""} PROMISE_REFRESH_FAILED:{exc}'[:2000]
        await db.flush()
        return await PlanningService.get_run(db, run.id)

    @staticmethod
    async def firm_planned_order(db: AsyncSession, planned_order_id: int) -> PlannedOrderDetail:
        planned_order = await planning_repo.get_planned_order(db, planned_order_id, lock=True)
        if not planned_order:
            raise errors.NotFoundError(msg='PLANNED_ORDER_NOT_FOUND')
        if planned_order.status == PlannedOrderStatus.FIRM:
            return PlannedOrderDetail.model_validate(planned_order)
        if planned_order.status != PlannedOrderStatus.PLANNED:
            raise errors.ConflictError(msg='PLANNED_ORDER_NOT_PLANNED')
        planned_order.status = PlannedOrderStatus.FIRM
        planned_order.firmed_at = timezone.now()
        planned_order.firmed_by = PlanningService._operator_id()
        await db.flush()
        return PlannedOrderDetail.model_validate(planned_order)

    @staticmethod
    async def release_planned_order(
        db: AsyncSession,
        planned_order_id: int,
        obj: ReleasePlannedOrder,
    ) -> PlannedOrderDetail:
        planned_order = await planning_repo.get_planned_order(db, planned_order_id, lock=True)
        if not planned_order:
            raise errors.NotFoundError(msg='PLANNED_ORDER_NOT_FOUND')
        if planned_order.status == PlannedOrderStatus.RELEASED:
            return PlannedOrderDetail.model_validate(planned_order)
        if planned_order.status not in (PlannedOrderStatus.PLANNED, PlannedOrderStatus.FIRM):
            raise errors.ConflictError(msg='PLANNED_ORDER_NOT_RELEASABLE')

        if planned_order.order_type == PlannedOrderType.PURCHASE:
            if not obj.supplier_id:
                raise errors.RequestError(msg='SUPPLIER_REQUIRED_FOR_PURCHASE_RELEASE')
            document = await purchasing_service.create_order(
                db,
                CreatePurchaseOrder(
                    supplier_id=obj.supplier_id,
                    currency=obj.currency,
                    remark=obj.remark or f'Released from {planned_order.planned_order_no}',
                    lines=[
                        CreatePurchaseOrderLine(
                            material_id=planned_order.material_id,
                            ordered_quantity=planned_order.quantity,
                            unit_price=obj.unit_price,
                            requested_delivery_at=datetime.combine(
                                planned_order.due_date, time.min, tzinfo=timezone.tz_info
                            ),
                        )
                    ],
                ),
            )
            source_type = 'PURCHASE_ORDER'
            source_id = document.id
            source_no = document.purchase_order_no
        else:
            if not planned_order.bom_id:
                raise errors.ConflictError(msg='PRODUCTION_PLANNED_ORDER_HAS_NO_BOM')
            routing_statement = select(Routing).where(
                Routing.product_material_id == planned_order.material_id,
                Routing.status == RoutingStatus.ACTIVE,
                Routing.deleted == 0,
            )
            if obj.routing_id:
                routing_statement = routing_statement.where(Routing.id == obj.routing_id)
            routing = await db.scalar(
                routing_statement.order_by(Routing.is_default.desc(), Routing.id.desc())
            )
            if not routing:
                raise errors.ConflictError(msg='ACTIVE_ROUTING_REQUIRED_FOR_PRODUCTION_RELEASE')
            document = await production_service.create_order(
                db,
                CreateWorkOrder(
                    product_material_id=planned_order.material_id,
                    bom_id=planned_order.bom_id,
                    routing_id=routing.id,
                    planned_quantity=planned_order.quantity,
                    planned_start_at=datetime.combine(
                        planned_order.release_date, time.min, tzinfo=timezone.tz_info
                    ),
                    planned_end_at=datetime.combine(
                        planned_order.due_date, time.min, tzinfo=timezone.tz_info
                    ),
                    remark=obj.remark or f'Released from {planned_order.planned_order_no}',
                ),
            )
            source_type = 'WORK_ORDER'
            source_id = document.id
            source_no = document.work_order_no

        planned_order.status = PlannedOrderStatus.RELEASED
        planned_order.source_document_type = source_type
        planned_order.source_document_id = source_id
        planned_order.source_document_no = source_no
        planned_order.released_at = timezone.now()
        planned_order.released_by = PlanningService._operator_id()
        run = await db.scalar(select(MrpRun).where(MrpRun.id == planned_order.mrp_run_id))
        try:
            refresh = await promise_service.recalculate_open_orders(db)
            if run:
                run.promise_refresh_at = refresh.assessed_at
                run.promise_assessment_count = refresh.assessed_line_count
        except Exception as exc:
            if run:
                run.error_message = f'{run.error_message or ""} PROMISE_REFRESH_FAILED:{exc}'[:2000]
        await db.flush()
        return PlannedOrderDetail.model_validate(planned_order)


planning_service = PlanningService()
