from decimal import Decimal, ROUND_CEILING
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.equipment.enums import (
    EquipmentStatus, EquipmentType, MoldCavityStatus, MoldCostType,
    MoldMaintenanceStatus, MoldMaintenanceTrigger, MoldMaintenanceType,
    MoldMountStatus, MoldQualityResult, MoldStatus,
)
from backend.plugin.equipment.model import (
    Equipment, MoldAsset, MoldCavity, MoldCavityQualityRecord, MoldCostLedger,
    MoldMaintenanceOrder, MoldMountRecord, MoldUsageRecord,
)
from backend.plugin.equipment.schema.mold import (
    CavityStatusUpdate, CompleteMoldMaintenance, CreateCavityQuality, CreateMold,
    CreateMoldMaintenance, MoldCavityDetail, MoldCavityQualityDetail, MoldCostAnalysis,
    MoldCostEntryDetail, MoldDashboard, MoldDetail, MoldMaintenanceDetail, MoldMountDetail,
    MoldStatusUpdate, MoldUsageDetail, MountMold, UnmountMold,
)
from backend.plugin.material.model import Material
from backend.plugin.production.enums import WorkOrderStatus
from backend.plugin.production.model import ProductionReport, WorkOrder
from backend.utils.timezone import timezone


class MoldService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    def _number(prefix: str) -> str:
        return f'{prefix}-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}'.upper()

    @staticmethod
    async def _mold(db: AsyncSession, mold_id: int, lock: bool = False) -> MoldAsset:
        stmt = select(MoldAsset).where(MoldAsset.id == mold_id, MoldAsset.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        mold = await db.scalar(stmt)
        if not mold:
            raise errors.NotFoundError(msg='MOLD_NOT_FOUND')
        return mold

    @staticmethod
    async def _post_cost(
        db: AsyncSession, mold: MoldAsset, cost_type: MoldCostType, amount: Decimal,
        source_type: str | None = None, source_id: int | None = None, description: str | None = None,
    ) -> MoldCostLedger | None:
        if amount <= 0:
            return None
        row = MoldCostLedger(
            entry_no=MoldService._number('MCL'), mold_id=mold.id, cost_type=cost_type,
            amount=amount, occurred_at=timezone.now(), source_type=source_type,
            source_id=source_id, description=description,
        )
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def dashboard(db: AsyncSession) -> MoldDashboard:
        molds = (await db.scalars(select(MoldAsset).where(MoldAsset.deleted == 0))).all()
        blocked = int(await db.scalar(select(func.count(MoldCavity.id)).where(
            MoldCavity.deleted == 0,
            MoldCavity.status.in_((MoldCavityStatus.BLOCKED, MoldCavityStatus.REPAIR)),
        )) or 0)
        open_orders = int(await db.scalar(select(func.count(MoldMaintenanceOrder.id)).where(
            MoldMaintenanceOrder.deleted == 0,
            MoldMaintenanceOrder.status.in_((MoldMaintenanceStatus.PLANNED, MoldMaintenanceStatus.IN_PROGRESS)),
        )) or 0)
        total_cost = await db.scalar(select(func.coalesce(func.sum(MoldCostLedger.amount), 0)).where(
            MoldCostLedger.deleted == 0
        ))
        return MoldDashboard(
            total_molds=len(molds),
            mounted_molds=sum(row.status == MoldStatus.MOUNTED for row in molds),
            maintenance_due=sum(row.shots_since_maintenance >= row.maintenance_interval_shots for row in molds),
            life_warning=sum(
                row.current_shots < row.designed_life_shots
                and Decimal(row.current_shots) * Decimal('100') / Decimal(row.designed_life_shots) >= row.warning_percent
                for row in molds
            ),
            life_exceeded=sum(row.current_shots >= row.designed_life_shots for row in molds),
            blocked_cavities=blocked,
            open_maintenance_orders=open_orders,
            total_lifecycle_cost=Decimal(total_cost or 0),
        )

    @staticmethod
    async def list_molds(db: AsyncSession, status: MoldStatus | None = None) -> list[MoldDetail]:
        stmt = select(MoldAsset).where(MoldAsset.deleted == 0)
        if status:
            stmt = stmt.where(MoldAsset.status == status)
        rows = (await db.scalars(stmt.order_by(MoldAsset.id.desc()))).all()
        return [MoldDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_mold(db: AsyncSession, obj: CreateMold) -> MoldDetail:
        code = obj.mold_code.strip().upper()
        if await db.scalar(select(MoldAsset.id).where(MoldAsset.mold_code == code, MoldAsset.deleted == 0)):
            raise errors.ConflictError(msg='MOLD_CODE_EXISTS')
        tool = await db.scalar(select(Equipment).where(
            Equipment.id == obj.tool_equipment_id, Equipment.deleted == 0
        ))
        if not tool or tool.equipment_type != EquipmentType.TOOL:
            raise errors.ConflictError(msg='MOLD_TOOL_EQUIPMENT_REQUIRED')
        if await db.scalar(select(MoldAsset.id).where(
            MoldAsset.tool_equipment_id == tool.id, MoldAsset.deleted == 0
        )):
            raise errors.ConflictError(msg='MOLD_TOOL_EQUIPMENT_ALREADY_USED')
        material = await db.scalar(select(Material).where(
            Material.id == obj.product_material_id, Material.deleted == 0
        ))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        mold = MoldAsset(
            mold_code=code, mold_name=obj.mold_name.strip(), tool_equipment_id=tool.id,
            product_material_id=material.id, mold_type=obj.mold_type.strip().upper(),
            cavity_count=obj.cavity_count, designed_life_shots=obj.designed_life_shots,
            maintenance_interval_shots=obj.maintenance_interval_shots,
            warning_percent=obj.warning_percent, acquisition_cost=obj.acquisition_cost,
            residual_value=obj.residual_value, commission_date=obj.commission_date,
            next_maintenance_shots=obj.maintenance_interval_shots,
            location=obj.location, manufacturer=obj.manufacturer, remark=obj.remark,
        )
        db.add(mold)
        await db.flush()
        for index in range(1, obj.cavity_count + 1):
            db.add(MoldCavity(mold_id=mold.id, cavity_no=str(index)))
        await db.flush()
        await MoldService._post_cost(
            db, mold, MoldCostType.ACQUISITION, obj.acquisition_cost,
            source_type='MOLD_ASSET', source_id=mold.id, description='模具购置成本',
        )
        return MoldDetail.model_validate(mold)

    @staticmethod
    async def update_status(db: AsyncSession, mold_id: int, obj: MoldStatusUpdate) -> MoldDetail:
        mold = await MoldService._mold(db, mold_id, lock=True)
        if mold.status == MoldStatus.MOUNTED:
            raise errors.ConflictError(msg='MOUNTED_MOLD_STATUS_LOCKED')
        if obj.status == MoldStatus.MOUNTED:
            raise errors.RequestError(msg='USE_MOLD_MOUNT_ACTION')
        mold.status = obj.status
        if obj.remark:
            mold.remark = obj.remark
        if obj.status == MoldStatus.SCRAPPED:
            await MoldService._post_cost(
                db, mold, MoldCostType.SCRAP, mold.residual_value,
                source_type='MOLD_ASSET', source_id=mold.id, description='模具报废残值',
            )
        await db.flush()
        return MoldDetail.model_validate(mold)

    @staticmethod
    async def list_cavities(db: AsyncSession, mold_id: int) -> list[MoldCavityDetail]:
        await MoldService._mold(db, mold_id)
        rows = (await db.scalars(select(MoldCavity).where(
            MoldCavity.mold_id == mold_id, MoldCavity.deleted == 0
        ).order_by(MoldCavity.id))).all()
        return [MoldCavityDetail.model_validate(row) for row in rows]

    @staticmethod
    async def update_cavity(db: AsyncSession, cavity_id: int, obj: CavityStatusUpdate) -> MoldCavityDetail:
        row = await db.scalar(select(MoldCavity).where(
            MoldCavity.id == cavity_id, MoldCavity.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='MOLD_CAVITY_NOT_FOUND')
        row.status = obj.status
        if obj.remark:
            row.remark = obj.remark
        await db.flush()
        return MoldCavityDetail.model_validate(row)

    @staticmethod
    async def mount(db: AsyncSession, mold_id: int, obj: MountMold) -> MoldMountDetail:
        mold = await MoldService._mold(db, mold_id, lock=True)
        if mold.status != MoldStatus.AVAILABLE:
            raise errors.ConflictError(msg='MOLD_NOT_AVAILABLE')
        if mold.current_shots >= mold.designed_life_shots:
            raise errors.ConflictError(msg='MOLD_LIFE_EXCEEDED')
        if mold.shots_since_maintenance >= mold.maintenance_interval_shots:
            raise errors.ConflictError(msg='MOLD_MAINTENANCE_DUE')
        machine = await db.scalar(select(Equipment).where(
            Equipment.id == obj.equipment_id, Equipment.deleted == 0
        ).with_for_update())
        if not machine or machine.equipment_type != EquipmentType.PRODUCTION or not machine.production_enabled:
            raise errors.ConflictError(msg='MOLD_PRODUCTION_EQUIPMENT_REQUIRED')
        if machine.status in (EquipmentStatus.DOWN, EquipmentStatus.MAINTENANCE, EquipmentStatus.OFFLINE, EquipmentStatus.DISABLED):
            raise errors.ConflictError(msg='MOLD_MACHINE_UNAVAILABLE')
        active_on_machine = await db.scalar(select(MoldMountRecord.id).where(
            MoldMountRecord.equipment_id == machine.id, MoldMountRecord.status == MoldMountStatus.MOUNTED,
            MoldMountRecord.deleted == 0,
        ))
        if active_on_machine:
            raise errors.ConflictError(msg='MOLD_MACHINE_ALREADY_OCCUPIED')
        if obj.work_order_id:
            order = await db.scalar(select(WorkOrder).where(
                WorkOrder.id == obj.work_order_id, WorkOrder.deleted == 0
            ))
            if not order or order.product_material_id != mold.product_material_id:
                raise errors.ConflictError(msg='MOLD_WORK_ORDER_PRODUCT_MISMATCH')
            if order.status not in (WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS):
                raise errors.ConflictError(msg='MOLD_WORK_ORDER_NOT_ACTIVE')
            active_for_order = await db.scalar(select(MoldMountRecord.id).where(
                MoldMountRecord.work_order_id == order.id,
                MoldMountRecord.status == MoldMountStatus.MOUNTED,
                MoldMountRecord.deleted == 0,
            ))
            if active_for_order:
                raise errors.ConflictError(msg='MOLD_WORK_ORDER_ALREADY_BOUND')
        row = MoldMountRecord(
            mount_no=MoldService._number('MMT'), mold_id=mold.id, equipment_id=machine.id,
            work_order_id=obj.work_order_id, mounted_at=obj.mounted_at or timezone.now(),
            opening_shots=mold.current_shots, mounted_by=MoldService._operator_id(), remark=obj.remark,
        )
        db.add(row)
        mold.status = MoldStatus.MOUNTED
        mold.mounted_equipment_id = machine.id
        await db.flush()
        return MoldMountDetail.model_validate(row)

    @staticmethod
    async def unmount(db: AsyncSession, mold_id: int, obj: UnmountMold) -> MoldMountDetail:
        mold = await MoldService._mold(db, mold_id, lock=True)
        row = await db.scalar(select(MoldMountRecord).where(
            MoldMountRecord.mold_id == mold.id, MoldMountRecord.status == MoldMountStatus.MOUNTED,
            MoldMountRecord.deleted == 0,
        ).with_for_update())
        if not row:
            raise errors.ConflictError(msg='MOLD_NOT_MOUNTED')
        row.status = MoldMountStatus.UNMOUNTED
        row.unmounted_at = timezone.now()
        row.unmounted_by = MoldService._operator_id()
        row.closing_shots = mold.current_shots
        if obj.remark:
            row.remark = obj.remark
        mold.mounted_equipment_id = None
        mold.status = (
            MoldStatus.SUSPENDED
            if mold.current_shots >= mold.designed_life_shots else MoldStatus.AVAILABLE
        )
        await db.flush()
        return MoldMountDetail.model_validate(row)

    @staticmethod
    async def list_mounts(db: AsyncSession, mold_id: int | None = None) -> list[MoldMountDetail]:
        stmt = select(MoldMountRecord).where(MoldMountRecord.deleted == 0)
        if mold_id:
            stmt = stmt.where(MoldMountRecord.mold_id == mold_id)
        rows = (await db.scalars(stmt.order_by(MoldMountRecord.id.desc()))).all()
        return [MoldMountDetail.model_validate(row) for row in rows]

    @staticmethod
    async def register_report_usage(db: AsyncSession, report: ProductionReport) -> MoldUsageRecord | None:
        existing = await db.scalar(select(MoldUsageRecord).where(
            MoldUsageRecord.production_report_id == report.id, MoldUsageRecord.deleted == 0
        ))
        if existing:
            return existing
        mount = await db.scalar(select(MoldMountRecord).where(
            MoldMountRecord.work_order_id == report.work_order_id,
            MoldMountRecord.status == MoldMountStatus.MOUNTED,
            MoldMountRecord.deleted == 0,
        ).with_for_update())
        if not mount:
            return None
        mold = await MoldService._mold(db, mount.mold_id, lock=True)
        if mold.current_shots >= mold.designed_life_shots:
            raise errors.ConflictError(msg='MOLD_LIFE_EXCEEDED')
        if mold.shots_since_maintenance >= mold.maintenance_interval_shots:
            raise errors.ConflictError(msg='MOLD_MAINTENANCE_DUE')
        cavities = (await db.scalars(select(MoldCavity).where(
            MoldCavity.mold_id == mold.id, MoldCavity.status == MoldCavityStatus.ACTIVE,
            MoldCavity.deleted == 0,
        ).with_for_update())).all()
        if not cavities:
            raise errors.ConflictError(msg='MOLD_NO_ACTIVE_CAVITY')
        total = report.good_quantity + report.scrap_quantity
        shots = int((total / Decimal(len(cavities))).to_integral_value(rounding=ROUND_CEILING))
        usage = MoldUsageRecord(
            mold_id=mold.id, mount_id=mount.id, work_order_id=report.work_order_id,
            production_report_id=report.id, shot_count=shots, active_cavity_count=len(cavities),
            good_quantity=report.good_quantity, scrap_quantity=report.scrap_quantity,
            reported_at=timezone.now(),
        )
        db.add(usage)
        mold.current_shots += shots
        mold.shots_since_maintenance += shots
        mold.next_maintenance_shots = mold.current_shots + max(
            mold.maintenance_interval_shots - mold.shots_since_maintenance, 0
        )
        mount.produced_quantity += total
        mount.good_quantity += report.good_quantity
        mount.scrap_quantity += report.scrap_quantity
        for cavity in cavities:
            cavity.current_shots += shots
        if mold.current_shots >= mold.designed_life_shots:
            mold.status = MoldStatus.SUSPENDED
        if mold.shots_since_maintenance >= mold.maintenance_interval_shots:
            open_order = await db.scalar(select(MoldMaintenanceOrder.id).where(
                MoldMaintenanceOrder.mold_id == mold.id,
                MoldMaintenanceOrder.status.in_((MoldMaintenanceStatus.PLANNED, MoldMaintenanceStatus.IN_PROGRESS)),
                MoldMaintenanceOrder.deleted == 0,
            ))
            if not open_order:
                db.add(MoldMaintenanceOrder(
                    order_no=MoldService._number('MMA'), mold_id=mold.id,
                    maintenance_type=MoldMaintenanceType.PREVENTIVE,
                    trigger_type=MoldMaintenanceTrigger.SHOT_COUNT,
                    description='模具达到冲次保养周期', due_shots=mold.current_shots,
                ))
        await db.flush()
        return usage

    @staticmethod
    async def list_usage(db: AsyncSession, mold_id: int | None = None) -> list[MoldUsageDetail]:
        stmt = select(MoldUsageRecord).where(MoldUsageRecord.deleted == 0)
        if mold_id:
            stmt = stmt.where(MoldUsageRecord.mold_id == mold_id)
        rows = (await db.scalars(stmt.order_by(MoldUsageRecord.id.desc()))).all()
        return [MoldUsageDetail.model_validate(row) for row in rows]

    @staticmethod
    async def create_maintenance(
        db: AsyncSession, mold_id: int, obj: CreateMoldMaintenance
    ) -> MoldMaintenanceDetail:
        mold = await MoldService._mold(db, mold_id)
        row = MoldMaintenanceOrder(
            order_no=MoldService._number('MMA'), mold_id=mold.id,
            maintenance_type=obj.maintenance_type, trigger_type=obj.trigger_type,
            description=obj.description, due_at=obj.due_at, due_shots=obj.due_shots,
            assigned_user_id=obj.assigned_user_id, remark=obj.remark,
        )
        db.add(row)
        await db.flush()
        return MoldMaintenanceDetail.model_validate(row)

    @staticmethod
    async def list_maintenance(db: AsyncSession, mold_id: int | None = None) -> list[MoldMaintenanceDetail]:
        stmt = select(MoldMaintenanceOrder).where(MoldMaintenanceOrder.deleted == 0)
        if mold_id:
            stmt = stmt.where(MoldMaintenanceOrder.mold_id == mold_id)
        rows = (await db.scalars(stmt.order_by(MoldMaintenanceOrder.id.desc()))).all()
        return [MoldMaintenanceDetail.model_validate(row) for row in rows]

    @staticmethod
    async def start_maintenance(db: AsyncSession, order_id: int) -> MoldMaintenanceDetail:
        row = await db.scalar(select(MoldMaintenanceOrder).where(
            MoldMaintenanceOrder.id == order_id, MoldMaintenanceOrder.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='MOLD_MAINTENANCE_NOT_FOUND')
        if row.status != MoldMaintenanceStatus.PLANNED:
            raise errors.ConflictError(msg='MOLD_MAINTENANCE_NOT_PLANNED')
        mold = await MoldService._mold(db, row.mold_id, lock=True)
        if mold.status == MoldStatus.MOUNTED:
            raise errors.ConflictError(msg='MOLD_MUST_BE_UNMOUNTED')
        row.status = MoldMaintenanceStatus.IN_PROGRESS
        row.started_at = timezone.now()
        mold.status = MoldStatus.MAINTENANCE if row.maintenance_type == MoldMaintenanceType.PREVENTIVE else MoldStatus.REPAIR
        await db.flush()
        return MoldMaintenanceDetail.model_validate(row)

    @staticmethod
    async def complete_maintenance(
        db: AsyncSession, order_id: int, obj: CompleteMoldMaintenance
    ) -> MoldMaintenanceDetail:
        row = await db.scalar(select(MoldMaintenanceOrder).where(
            MoldMaintenanceOrder.id == order_id, MoldMaintenanceOrder.deleted == 0
        ).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='MOLD_MAINTENANCE_NOT_FOUND')
        if row.status != MoldMaintenanceStatus.IN_PROGRESS:
            raise errors.ConflictError(msg='MOLD_MAINTENANCE_NOT_IN_PROGRESS')
        mold = await MoldService._mold(db, row.mold_id, lock=True)
        total = obj.labor_cost + obj.material_cost + obj.external_cost
        row.status = MoldMaintenanceStatus.COMPLETED
        row.completed_at = timezone.now()
        row.findings = obj.findings
        row.action_taken = obj.action_taken
        row.labor_cost, row.material_cost, row.external_cost, row.total_cost = (
            obj.labor_cost, obj.material_cost, obj.external_cost, total
        )
        mold.shots_since_maintenance = 0
        mold.last_maintenance_at = row.completed_at
        mold.next_maintenance_shots = mold.current_shots + mold.maintenance_interval_shots
        mold.status = MoldStatus.SUSPENDED if mold.current_shots >= mold.designed_life_shots else MoldStatus.AVAILABLE
        await db.flush()
        await MoldService._post_cost(
            db, mold,
            MoldCostType.MAINTENANCE if row.maintenance_type == MoldMaintenanceType.PREVENTIVE else MoldCostType.REPAIR,
            total, source_type='MOLD_MAINTENANCE', source_id=row.id, description=row.action_taken,
        )
        return MoldMaintenanceDetail.model_validate(row)

    @staticmethod
    async def record_cavity_quality(
        db: AsyncSession, mold_id: int, obj: CreateCavityQuality
    ) -> MoldCavityQualityDetail:
        mold = await MoldService._mold(db, mold_id, lock=True)
        cavity = await db.scalar(select(MoldCavity).where(
            MoldCavity.id == obj.cavity_id, MoldCavity.mold_id == mold.id,
            MoldCavity.deleted == 0,
        ).with_for_update())
        if not cavity:
            raise errors.NotFoundError(msg='MOLD_CAVITY_NOT_FOUND')
        now = timezone.now()
        row = MoldCavityQualityRecord(
            mold_id=mold.id, cavity_id=cavity.id, inspected_quantity=obj.inspected_quantity,
            defect_quantity=obj.defect_quantity, result=obj.result, checked_at=now,
            work_order_id=obj.work_order_id, production_report_id=obj.production_report_id,
            inspection_id=obj.inspection_id, defect_code=obj.defect_code, notes=obj.notes,
        )
        db.add(row)
        cavity.inspected_quantity += obj.inspected_quantity
        cavity.defect_quantity += obj.defect_quantity
        if obj.result == MoldQualityResult.FAIL:
            cavity.status = MoldCavityStatus.BLOCKED
            cavity.last_defect_at = now
            cavity.last_defect_code = obj.defect_code
            open_repair = await db.scalar(select(MoldMaintenanceOrder.id).where(
                MoldMaintenanceOrder.mold_id == mold.id,
                MoldMaintenanceOrder.maintenance_type == MoldMaintenanceType.REPAIR,
                MoldMaintenanceOrder.status.in_((MoldMaintenanceStatus.PLANNED, MoldMaintenanceStatus.IN_PROGRESS)),
                MoldMaintenanceOrder.deleted == 0,
            ))
            if not open_repair:
                db.add(MoldMaintenanceOrder(
                    order_no=MoldService._number('MMR'), mold_id=mold.id,
                    maintenance_type=MoldMaintenanceType.REPAIR,
                    trigger_type=MoldMaintenanceTrigger.QUALITY,
                    description=f'穴位 {cavity.cavity_no} 质量异常：{obj.defect_code or "未分类缺陷"}',
                ))
            active_count = int(await db.scalar(select(func.count(MoldCavity.id)).where(
                MoldCavity.mold_id == mold.id, MoldCavity.status == MoldCavityStatus.ACTIVE,
                MoldCavity.deleted == 0,
            )) or 0)
            if active_count == 0:
                mold.status = MoldStatus.SUSPENDED
        await db.flush()
        return MoldCavityQualityDetail.model_validate(row)

    @staticmethod
    async def list_quality(db: AsyncSession, mold_id: int | None = None) -> list[MoldCavityQualityDetail]:
        stmt = select(MoldCavityQualityRecord).where(MoldCavityQualityRecord.deleted == 0)
        if mold_id:
            stmt = stmt.where(MoldCavityQualityRecord.mold_id == mold_id)
        rows = (await db.scalars(stmt.order_by(MoldCavityQualityRecord.id.desc()))).all()
        return [MoldCavityQualityDetail.model_validate(row) for row in rows]

    @staticmethod
    async def list_costs(db: AsyncSession, mold_id: int | None = None) -> list[MoldCostEntryDetail]:
        stmt = select(MoldCostLedger).where(MoldCostLedger.deleted == 0)
        if mold_id:
            stmt = stmt.where(MoldCostLedger.mold_id == mold_id)
        rows = (await db.scalars(stmt.order_by(MoldCostLedger.id.desc()))).all()
        return [MoldCostEntryDetail.model_validate(row) for row in rows]

    @staticmethod
    async def cost_analysis(db: AsyncSession, mold_id: int) -> MoldCostAnalysis:
        mold = await MoldService._mold(db, mold_id)
        rows = (await db.scalars(select(MoldCostLedger).where(
            MoldCostLedger.mold_id == mold.id, MoldCostLedger.deleted == 0
        ))).all()
        totals = {kind: sum((row.amount for row in rows if row.cost_type == kind), Decimal('0')) for kind in MoldCostType}
        total = sum((row.amount for row in rows), Decimal('0'))
        return MoldCostAnalysis(
            mold_id=mold.id, acquisition_cost=totals[MoldCostType.ACQUISITION],
            maintenance_cost=totals[MoldCostType.MAINTENANCE], repair_cost=totals[MoldCostType.REPAIR],
            modification_cost=totals[MoldCostType.MODIFICATION], total_lifecycle_cost=total,
            current_shots=mold.current_shots,
            cost_per_shot=(total / Decimal(mold.current_shots)).quantize(Decimal('0.0001')) if mold.current_shots else Decimal('0'),
        )


mold_service = MoldService()
