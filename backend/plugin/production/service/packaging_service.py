from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.material.model import Material
from backend.plugin.production.model import (
    PackagingHandlingUnit, PackagingHandlingUnitContent, PackagingInspection,
    PackagingLabelPrint, PackagingSpecification, PackagingTask, PackagingWeightRecord,
    ProductionReport, WorkOrder,
)
from backend.plugin.production.packaging_enums import (
    HandlingUnitStatus, HandlingUnitType, PackagingInspectionResult, PackagingScanType,
    PackagingSpecStatus, PackagingTaskStatus, WeightCheckResult,
)
from backend.plugin.production.schema.packaging import (
    CreateHandlingUnit, CreatePackagingSpecification, CreatePackagingTask, InspectHandlingUnit,
    PackagingContentDetail, PackagingDashboard, PackagingHandlingUnitDetail,
    PackagingTaskDetail, PrintPackagingLabel, RecordPackagingWeight, ReopenHandlingUnit,
    ScanPackagingItem, SealHandlingUnit,
)
from backend.plugin.trace.enums import LotStatus, QualityStatus, SerialStatus
from backend.plugin.trace.model import MaterialLot, MaterialSerial
from backend.utils.timezone import timezone


class PackagingService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _spec(db: AsyncSession, spec_id: int, *, lock: bool = False) -> PackagingSpecification:
        stmt = select(PackagingSpecification).where(
            PackagingSpecification.id == spec_id, PackagingSpecification.deleted == 0
        )
        if lock:
            stmt = stmt.with_for_update()
        spec = await db.scalar(stmt)
        if not spec:
            raise errors.NotFoundError(msg='PACKAGING_SPEC_NOT_FOUND')
        return spec

    @staticmethod
    async def _task(db: AsyncSession, task_id: int, *, lock: bool = False) -> PackagingTask:
        stmt = select(PackagingTask).where(PackagingTask.id == task_id, PackagingTask.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        task = await db.scalar(stmt)
        if not task:
            raise errors.NotFoundError(msg='PACKAGING_TASK_NOT_FOUND')
        return task

    @staticmethod
    async def _hu(db: AsyncSession, hu_id: int, *, lock: bool = False) -> PackagingHandlingUnit:
        stmt = select(PackagingHandlingUnit).where(
            PackagingHandlingUnit.id == hu_id, PackagingHandlingUnit.deleted == 0
        )
        if lock:
            stmt = stmt.with_for_update()
        hu = await db.scalar(stmt)
        if not hu:
            raise errors.NotFoundError(msg='PACKAGING_HU_NOT_FOUND')
        return hu

    @staticmethod
    async def _hu_detail(db: AsyncSession, hu: PackagingHandlingUnit) -> PackagingHandlingUnitDetail:
        contents = (await db.scalars(
            select(PackagingHandlingUnitContent).where(
                PackagingHandlingUnitContent.hu_id == hu.id,
                PackagingHandlingUnitContent.deleted == 0,
            ).order_by(PackagingHandlingUnitContent.id)
        )).all()
        detail = PackagingHandlingUnitDetail.model_validate(hu)
        detail.contents = [PackagingContentDetail.model_validate(item) for item in contents]
        return detail

    @staticmethod
    async def _task_detail(db: AsyncSession, task: PackagingTask) -> PackagingTaskDetail:
        units = (await db.scalars(
            select(PackagingHandlingUnit).where(
                PackagingHandlingUnit.task_id == task.id, PackagingHandlingUnit.deleted == 0
            ).order_by(PackagingHandlingUnit.id)
        )).all()
        detail = PackagingTaskDetail.model_validate(task)
        detail.handling_units = [await PackagingService._hu_detail(db, item) for item in units]
        return detail

    @staticmethod
    async def list_specifications(
        db: AsyncSession, material_id: int | None = None, status: str | None = None
    ) -> Sequence[PackagingSpecification]:
        stmt = select(PackagingSpecification).where(PackagingSpecification.deleted == 0)
        if material_id:
            stmt = stmt.where(PackagingSpecification.material_id == material_id)
        if status:
            stmt = stmt.where(PackagingSpecification.status == status)
        return (await db.scalars(stmt.order_by(PackagingSpecification.id.desc()))).all()

    @staticmethod
    async def create_specification(
        db: AsyncSession, obj: CreatePackagingSpecification
    ) -> PackagingSpecification:
        material = await db.scalar(select(Material).where(Material.id == obj.material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        exists = await db.scalar(select(PackagingSpecification.id).where(
            PackagingSpecification.spec_code == obj.spec_code.upper(),
            PackagingSpecification.version == obj.version.upper(),
            PackagingSpecification.deleted == 0,
        ))
        if exists:
            raise errors.ConflictError(msg='PACKAGING_SPEC_VERSION_EXISTS')
        spec = PackagingSpecification(
            spec_code=obj.spec_code.upper(), spec_name=obj.spec_name, material_id=obj.material_id,
            units_per_carton=obj.units_per_carton, version=obj.version.upper(),
            cartons_per_pallet=obj.cartons_per_pallet, allow_mixed_lot=obj.allow_mixed_lot,
            allow_partial_carton=obj.allow_partial_carton,
            require_quality_release=obj.require_quality_release,
            require_weight_check=obj.require_weight_check,
            target_gross_weight=obj.target_gross_weight, weight_tolerance=obj.weight_tolerance,
            label_template_code=obj.label_template_code, effective_from=obj.effective_from,
            effective_to=obj.effective_to, remark=obj.remark,
        )
        db.add(spec)
        await db.flush()
        return spec

    @staticmethod
    async def set_specification_status(
        db: AsyncSession, spec_id: int, status: PackagingSpecStatus
    ) -> PackagingSpecification:
        spec = await PackagingService._spec(db, spec_id, lock=True)
        spec.status = status
        await db.flush()
        return spec

    @staticmethod
    async def list_tasks(db: AsyncSession, status: str | None = None) -> list[PackagingTaskDetail]:
        stmt = select(PackagingTask).where(PackagingTask.deleted == 0)
        if status:
            stmt = stmt.where(PackagingTask.status == status)
        tasks = (await db.scalars(stmt.order_by(PackagingTask.id.desc()))).all()
        return [await PackagingService._task_detail(db, item) for item in tasks]

    @staticmethod
    async def get_task(db: AsyncSession, task_id: int) -> PackagingTaskDetail:
        return await PackagingService._task_detail(db, await PackagingService._task(db, task_id))

    @staticmethod
    async def create_task(db: AsyncSession, obj: CreatePackagingTask) -> PackagingTaskDetail:
        if obj.idempotency_key:
            existing = await db.scalar(select(PackagingTask).where(
                PackagingTask.idempotency_key == obj.idempotency_key, PackagingTask.deleted == 0
            ))
            if existing:
                if (
                    existing.production_report_id != obj.production_report_id
                    or existing.specification_id != obj.specification_id
                    or existing.planned_quantity != obj.planned_quantity
                ):
                    raise errors.ConflictError(msg='PACKAGING_TASK_IDEMPOTENCY_CONFLICT')
                return await PackagingService._task_detail(db, existing)
        report = await db.scalar(select(ProductionReport).where(
            ProductionReport.id == obj.production_report_id, ProductionReport.deleted == 0
        ).with_for_update())
        if not report:
            raise errors.NotFoundError(msg='PRODUCTION_REPORT_NOT_FOUND')
        order = await db.scalar(select(WorkOrder).where(WorkOrder.id == report.work_order_id, WorkOrder.deleted == 0))
        if not order:
            raise errors.NotFoundError(msg='WORK_ORDER_NOT_FOUND')
        spec = await PackagingService._spec(db, obj.specification_id)
        if spec.status != PackagingSpecStatus.ACTIVE or spec.material_id != order.product_material_id:
            raise errors.ConflictError(msg='PACKAGING_SPEC_NOT_ACTIVE_FOR_PRODUCT')
        already_planned = await db.scalar(select(func.coalesce(func.sum(PackagingTask.planned_quantity), 0)).where(
            PackagingTask.production_report_id == report.id,
            PackagingTask.status != PackagingTaskStatus.CANCELLED,
            PackagingTask.deleted == 0,
        ))
        if Decimal(already_planned) + obj.planned_quantity > report.good_quantity:
            raise errors.ConflictError(msg='PACKAGING_QUANTITY_EXCEEDS_REPORT_GOOD_QUANTITY')
        number = (obj.task_no or f'PKG-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(PackagingTask.id).where(
            PackagingTask.task_no == number, PackagingTask.deleted == 0
        )):
            raise errors.ConflictError(msg='PACKAGING_TASK_NO_EXISTS')
        task = PackagingTask(
            task_no=number, production_report_id=report.id, work_order_id=order.id,
            material_id=order.product_material_id, specification_id=spec.id,
            planned_quantity=obj.planned_quantity, lot_id=report.lot_id,
            stock_transaction_id=report.stock_transaction_id,
            idempotency_key=obj.idempotency_key, remark=obj.remark,
        )
        db.add(task)
        await db.flush()
        return await PackagingService._task_detail(db, task)

    @staticmethod
    async def release_task(db: AsyncSession, task_id: int) -> PackagingTaskDetail:
        task = await PackagingService._task(db, task_id, lock=True)
        if task.status == PackagingTaskStatus.RELEASED:
            return await PackagingService._task_detail(db, task)
        if task.status != PackagingTaskStatus.DRAFT:
            raise errors.ConflictError(msg='PACKAGING_TASK_NOT_DRAFT')
        spec = await PackagingService._spec(db, task.specification_id)
        if spec.status != PackagingSpecStatus.ACTIVE:
            raise errors.ConflictError(msg='PACKAGING_SPEC_NOT_ACTIVE')
        if task.lot_id:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == task.lot_id, MaterialLot.deleted == 0))
            if not lot or lot.status != LotStatus.ACTIVE:
                raise errors.ConflictError(msg='PACKAGING_LOT_NOT_ACTIVE')
            if spec.require_quality_release and lot.quality_status != QualityStatus.PASS:
                raise errors.ConflictError(msg='PACKAGING_LOT_NOT_QUALITY_RELEASED')
            if lot.expiry_date and lot.expiry_date <= timezone.now():
                raise errors.ConflictError(msg='PACKAGING_LOT_EXPIRED')
        task.status = PackagingTaskStatus.RELEASED
        await db.flush()
        return await PackagingService._task_detail(db, task)

    @staticmethod
    async def start_task(db: AsyncSession, task_id: int) -> PackagingTaskDetail:
        task = await PackagingService._task(db, task_id, lock=True)
        if task.status == PackagingTaskStatus.IN_PROGRESS:
            return await PackagingService._task_detail(db, task)
        if task.status != PackagingTaskStatus.RELEASED:
            raise errors.ConflictError(msg='PACKAGING_TASK_NOT_RELEASED')
        task.status = PackagingTaskStatus.IN_PROGRESS
        task.started_at = timezone.now()
        await db.flush()
        return await PackagingService._task_detail(db, task)

    @staticmethod
    async def create_handling_unit(
        db: AsyncSession, task_id: int, obj: CreateHandlingUnit
    ) -> PackagingHandlingUnitDetail:
        task = await PackagingService._task(db, task_id, lock=True)
        if task.status not in (PackagingTaskStatus.RELEASED, PackagingTaskStatus.IN_PROGRESS):
            raise errors.ConflictError(msg='PACKAGING_TASK_NOT_OPEN')
        spec = await PackagingService._spec(db, task.specification_id)
        capacity = obj.capacity or (spec.units_per_carton if obj.hu_type == HandlingUnitType.CARTON else task.planned_quantity)
        if obj.parent_hu_id:
            parent = await PackagingService._hu(db, obj.parent_hu_id)
            if parent.task_id != task.id or parent.status != HandlingUnitStatus.OPEN:
                raise errors.ConflictError(msg='PACKAGING_PARENT_HU_INVALID')
        code = (obj.hu_code or f'HU-{obj.hu_type.value}-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(PackagingHandlingUnit.id).where(
            PackagingHandlingUnit.hu_code == code, PackagingHandlingUnit.deleted == 0
        )):
            raise errors.ConflictError(msg='PACKAGING_HU_CODE_EXISTS')
        hu = PackagingHandlingUnit(
            hu_code=code, task_id=task.id, hu_type=obj.hu_type, capacity=capacity,
            parent_hu_id=obj.parent_hu_id, remark=obj.remark,
        )
        db.add(hu)
        if task.status == PackagingTaskStatus.RELEASED:
            task.status = PackagingTaskStatus.IN_PROGRESS
            task.started_at = timezone.now()
        await db.flush()
        return await PackagingService._hu_detail(db, hu)

    @staticmethod
    async def get_handling_unit(db: AsyncSession, hu_code: str) -> PackagingHandlingUnitDetail:
        hu = await db.scalar(select(PackagingHandlingUnit).where(
            PackagingHandlingUnit.hu_code == hu_code.upper(), PackagingHandlingUnit.deleted == 0
        ))
        if not hu:
            raise errors.NotFoundError(msg='PACKAGING_HU_NOT_FOUND')
        return await PackagingService._hu_detail(db, hu)

    @staticmethod
    async def scan_item(
        db: AsyncSession, hu_id: int, obj: ScanPackagingItem
    ) -> PackagingHandlingUnitDetail:
        existing = await db.scalar(select(PackagingHandlingUnitContent).where(
            PackagingHandlingUnitContent.scan_key == obj.idempotency_key,
            PackagingHandlingUnitContent.deleted == 0,
        ))
        if existing:
            requested_quantity = obj.quantity
            if existing.scan_type == PackagingScanType.SERIAL and requested_quantity is None:
                requested_quantity = Decimal('1')
            if (
                existing.hu_id != hu_id
                or existing.scanned_code != obj.code
                or existing.quantity != requested_quantity
            ):
                raise errors.ConflictError(msg='PACKAGING_SCAN_KEY_REUSED')
            return await PackagingService._hu_detail(db, await PackagingService._hu(db, hu_id))
        hu = await PackagingService._hu(db, hu_id, lock=True)
        if hu.status != HandlingUnitStatus.OPEN:
            raise errors.ConflictError(msg='PACKAGING_HU_NOT_OPEN')
        task = await PackagingService._task(db, hu.task_id, lock=True)
        if task.status not in (PackagingTaskStatus.RELEASED, PackagingTaskStatus.IN_PROGRESS):
            raise errors.ConflictError(msg='PACKAGING_TASK_NOT_OPEN')
        spec = await PackagingService._spec(db, task.specification_id)
        serial = await db.scalar(select(MaterialSerial).where(
            MaterialSerial.serial_no == obj.code, MaterialSerial.deleted == 0
        ))
        lot: MaterialLot | None
        if serial:
            if obj.quantity is not None and obj.quantity != Decimal('1'):
                raise errors.ConflictError(msg='SERIAL_SCAN_QUANTITY_MUST_BE_ONE')
            if serial.status != SerialStatus.ACTIVE:
                raise errors.ConflictError(msg='PACKAGING_SERIAL_NOT_ACTIVE')
            if spec.require_quality_release and serial.quality_status != QualityStatus.PASS:
                raise errors.ConflictError(msg='PACKAGING_SERIAL_NOT_QUALITY_RELEASED')
            duplicate = await db.scalar(
                select(PackagingHandlingUnitContent.id)
                .join(PackagingHandlingUnit, PackagingHandlingUnit.id == PackagingHandlingUnitContent.hu_id)
                .where(
                    PackagingHandlingUnitContent.serial_id == serial.id,
                    PackagingHandlingUnitContent.deleted == 0,
                    PackagingHandlingUnit.status != HandlingUnitStatus.VOIDED,
                    PackagingHandlingUnit.deleted == 0,
                )
            )
            if duplicate:
                raise errors.ConflictError(msg='PACKAGING_SERIAL_ALREADY_PACKED')
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == serial.lot_id, MaterialLot.deleted == 0)) if serial.lot_id else None
            scan_type, quantity = PackagingScanType.SERIAL, Decimal('1')
        else:
            lot = await db.scalar(select(MaterialLot).where(
                MaterialLot.lot_no == obj.code, MaterialLot.deleted == 0
            ))
            if not lot:
                raise errors.NotFoundError(msg='PACKAGING_LOT_OR_SERIAL_NOT_FOUND')
            if obj.quantity is None:
                raise errors.ConflictError(msg='LOT_SCAN_QUANTITY_REQUIRED')
            scan_type, quantity = PackagingScanType.LOT, obj.quantity
        if (serial and serial.material_id != task.material_id) or (lot and lot.material_id != task.material_id):
            raise errors.ConflictError(msg='PACKAGING_MATERIAL_MISMATCH')
        if lot:
            if lot.status != LotStatus.ACTIVE:
                raise errors.ConflictError(msg='PACKAGING_LOT_NOT_ACTIVE')
            if spec.require_quality_release and lot.quality_status != QualityStatus.PASS:
                raise errors.ConflictError(msg='PACKAGING_LOT_NOT_QUALITY_RELEASED')
            if lot.expiry_date and lot.expiry_date <= timezone.now():
                raise errors.ConflictError(msg='PACKAGING_LOT_EXPIRED')
            # A task is sourced by one immutable production report. Even if the
            # specification supports mixed lots, cross-report packing must use a
            # future consolidation task instead of falsifying this report link.
            if task.lot_id and lot.id != task.lot_id:
                raise errors.ConflictError(msg='PACKAGING_LOT_NOT_FROM_REPORT')
        if hu.quantity + quantity > hu.capacity:
            raise errors.ConflictError(msg='PACKAGING_HU_CAPACITY_EXCEEDED')
        if task.packed_quantity + quantity > task.planned_quantity:
            raise errors.ConflictError(msg='PACKAGING_TASK_QUANTITY_EXCEEDED')
        content = PackagingHandlingUnitContent(
            hu_id=hu.id, material_id=task.material_id, production_report_id=task.production_report_id,
            scan_type=scan_type, scanned_code=obj.code, quantity=quantity,
            scan_key=obj.idempotency_key, lot_id=lot.id if lot else None,
            serial_id=serial.id if serial else None, scanned_by=PackagingService._operator_id(),
        )
        db.add(content)
        hu.quantity += quantity
        hu.version += 1
        task.packed_quantity += quantity
        if task.status == PackagingTaskStatus.RELEASED:
            task.status = PackagingTaskStatus.IN_PROGRESS
            task.started_at = timezone.now()
        await db.flush()
        return await PackagingService._hu_detail(db, hu)

    @staticmethod
    async def record_weight(
        db: AsyncSession, hu_id: int, obj: RecordPackagingWeight
    ) -> PackagingWeightRecord:
        existing = await db.scalar(select(PackagingWeightRecord).where(
            PackagingWeightRecord.idempotency_key == obj.idempotency_key,
            PackagingWeightRecord.deleted == 0,
        ))
        if existing:
            if (
                existing.hu_id != hu_id
                or existing.gross_weight != obj.gross_weight
                or existing.tare_weight != obj.tare_weight
            ):
                raise errors.ConflictError(msg='PACKAGING_WEIGHT_IDEMPOTENCY_CONFLICT')
            return existing
        hu = await PackagingService._hu(db, hu_id, lock=True)
        if hu.status != HandlingUnitStatus.OPEN:
            raise errors.ConflictError(msg='PACKAGING_HU_NOT_OPEN')
        task = await PackagingService._task(db, hu.task_id)
        spec = await PackagingService._spec(db, task.specification_id)
        net = obj.gross_weight - obj.tare_weight
        if spec.require_weight_check:
            lower = spec.target_gross_weight - spec.weight_tolerance
            upper = spec.target_gross_weight + spec.weight_tolerance
            result = WeightCheckResult.PASS if lower <= obj.gross_weight <= upper else WeightCheckResult.FAIL
        else:
            result = WeightCheckResult.NOT_REQUIRED
        record = PackagingWeightRecord(
            hu_id=hu.id, gross_weight=obj.gross_weight, tare_weight=obj.tare_weight,
            net_weight=net, result=result, idempotency_key=obj.idempotency_key,
            measured_by=PackagingService._operator_id(), remark=obj.remark,
        )
        db.add(record)
        hu.gross_weight, hu.tare_weight, hu.net_weight, hu.weight_result = obj.gross_weight, obj.tare_weight, net, result
        hu.version += 1
        await db.flush()
        return record

    @staticmethod
    async def seal_handling_unit(
        db: AsyncSession, hu_id: int, obj: SealHandlingUnit
    ) -> PackagingHandlingUnitDetail:
        hu = await PackagingService._hu(db, hu_id, lock=True)
        if hu.status == HandlingUnitStatus.SEALED:
            return await PackagingService._hu_detail(db, hu)
        if hu.status != HandlingUnitStatus.OPEN or hu.quantity <= 0:
            raise errors.ConflictError(msg='PACKAGING_HU_NOT_SEALABLE')
        task = await PackagingService._task(db, hu.task_id, lock=True)
        spec = await PackagingService._spec(db, task.specification_id)
        if hu.quantity < hu.capacity and not spec.allow_partial_carton:
            raise errors.ConflictError(msg='PARTIAL_CARTON_NOT_ALLOWED')
        if spec.require_weight_check and hu.weight_result != WeightCheckResult.PASS:
            raise errors.ConflictError(msg='PACKAGING_WEIGHT_CHECK_NOT_PASSED')
        hu.status = HandlingUnitStatus.SEALED
        hu.sealed_at = timezone.now()
        hu.version += 1
        if obj.remark:
            hu.remark = obj.remark
        if task.packed_quantity == task.planned_quantity:
            task.status = PackagingTaskStatus.PACKED
            task.packed_at = timezone.now()
        await db.flush()
        return await PackagingService._hu_detail(db, hu)

    @staticmethod
    async def reopen_handling_unit(
        db: AsyncSession, hu_id: int, obj: ReopenHandlingUnit
    ) -> PackagingHandlingUnitDetail:
        hu = await PackagingService._hu(db, hu_id, lock=True)
        if hu.status != HandlingUnitStatus.SEALED:
            raise errors.ConflictError(msg='ONLY_SEALED_HU_CAN_REOPEN')
        task = await PackagingService._task(db, hu.task_id, lock=True)
        if task.status == PackagingTaskStatus.RELEASED_TO_STOCK:
            raise errors.ConflictError(msg='STORED_PACKAGING_CANNOT_REOPEN')
        hu.status = HandlingUnitStatus.OPEN
        hu.sealed_at = None
        hu.remark = obj.reason
        hu.version += 1
        task.status = PackagingTaskStatus.IN_PROGRESS
        task.packed_at = None
        await db.flush()
        return await PackagingService._hu_detail(db, hu)

    @staticmethod
    async def inspect_handling_unit(
        db: AsyncSession, hu_id: int, obj: InspectHandlingUnit
    ) -> PackagingInspection:
        existing = await db.scalar(select(PackagingInspection).where(
            PackagingInspection.idempotency_key == obj.idempotency_key,
            PackagingInspection.deleted == 0,
        ))
        if existing:
            if existing.hu_id != hu_id or existing.result != obj.result:
                raise errors.ConflictError(msg='PACKAGING_INSPECTION_IDEMPOTENCY_CONFLICT')
            return existing
        hu = await PackagingService._hu(db, hu_id, lock=True)
        if hu.status not in (HandlingUnitStatus.SEALED, HandlingUnitStatus.QUALITY_HOLD):
            raise errors.ConflictError(msg='PACKAGING_HU_NOT_INSPECTABLE')
        if obj.result == PackagingInspectionResult.PASS and not (
            obj.appearance_passed and obj.quantity_passed and obj.label_passed
        ):
            raise errors.ConflictError(msg='PACKAGING_PASS_CHECKS_INCONSISTENT')
        inspection = PackagingInspection(
            hu_id=hu.id, result=obj.result, idempotency_key=obj.idempotency_key,
            appearance_passed=obj.appearance_passed, quantity_passed=obj.quantity_passed,
            label_passed=obj.label_passed, inspected_by=PackagingService._operator_id(), notes=obj.notes,
        )
        db.add(inspection)
        if obj.result == PackagingInspectionResult.PASS:
            hu.status, hu.released_at = HandlingUnitStatus.RELEASED, timezone.now()
        else:
            hu.status = HandlingUnitStatus.QUALITY_HOLD
        hu.version += 1
        await db.flush()
        return inspection

    @staticmethod
    async def print_label(
        db: AsyncSession, hu_id: int, obj: PrintPackagingLabel
    ) -> PackagingLabelPrint:
        existing = await db.scalar(select(PackagingLabelPrint).where(
            PackagingLabelPrint.idempotency_key == obj.idempotency_key,
            PackagingLabelPrint.deleted == 0,
        ))
        if existing:
            if existing.hu_id != hu_id or existing.copies != obj.copies:
                raise errors.ConflictError(msg='PACKAGING_LABEL_IDEMPOTENCY_CONFLICT')
            return existing
        hu = await PackagingService._hu(db, hu_id)
        if hu.status == HandlingUnitStatus.OPEN:
            raise errors.ConflictError(msg='PACKAGING_LABEL_REQUIRES_SEALED_HU')
        task = await PackagingService._task(db, hu.task_id)
        spec = await PackagingService._spec(db, task.specification_id)
        template = obj.template_code or spec.label_template_code
        if not template:
            raise errors.ConflictError(msg='PACKAGING_LABEL_TEMPLATE_REQUIRED')
        record = PackagingLabelPrint(
            hu_id=hu.id, template_code=template, copies=obj.copies,
            printer_name=obj.printer_name, idempotency_key=obj.idempotency_key,
            printed_by=PackagingService._operator_id(), reason=obj.reason,
        )
        db.add(record)
        await db.flush()
        return record

    @staticmethod
    async def release_to_stock(db: AsyncSession, task_id: int) -> PackagingTaskDetail:
        task = await PackagingService._task(db, task_id, lock=True)
        if task.status == PackagingTaskStatus.RELEASED_TO_STOCK:
            return await PackagingService._task_detail(db, task)
        if task.packed_quantity != task.planned_quantity or not task.stock_transaction_id:
            raise errors.ConflictError(msg='PACKAGING_TASK_NOT_READY_FOR_STOCK')
        spec = await PackagingService._spec(db, task.specification_id)
        units = (await db.scalars(select(PackagingHandlingUnit).where(
            PackagingHandlingUnit.task_id == task.id,
            PackagingHandlingUnit.deleted == 0,
            PackagingHandlingUnit.status != HandlingUnitStatus.VOIDED,
        ).with_for_update())).all()
        if not units:
            raise errors.ConflictError(msg='PACKAGING_TASK_HAS_NO_HU')
        allowed = {HandlingUnitStatus.RELEASED} if spec.require_quality_release else {
            HandlingUnitStatus.SEALED, HandlingUnitStatus.RELEASED
        }
        if any(item.status not in allowed for item in units):
            raise errors.ConflictError(msg='PACKAGING_HU_NOT_RELEASED')
        # ProductionReport already posted the stock quantity. Packaging release links that
        # immutable transaction and changes HU availability only; it must not post it twice.
        now = timezone.now()
        for item in units:
            item.status, item.stored_at, item.version = HandlingUnitStatus.STORED, now, item.version + 1
        task.status, task.released_at = PackagingTaskStatus.RELEASED_TO_STOCK, now
        await db.flush()
        return await PackagingService._task_detail(db, task)

    @staticmethod
    async def dashboard(db: AsyncSession) -> PackagingDashboard:
        tasks = (await db.scalars(select(PackagingTask).where(PackagingTask.deleted == 0))).all()
        units = (await db.scalars(select(PackagingHandlingUnit).where(PackagingHandlingUnit.deleted == 0))).all()
        return PackagingDashboard(
            draft_tasks=sum(item.status == PackagingTaskStatus.DRAFT for item in tasks),
            active_tasks=sum(item.status in (PackagingTaskStatus.RELEASED, PackagingTaskStatus.IN_PROGRESS) for item in tasks),
            packed_tasks=sum(item.status == PackagingTaskStatus.PACKED for item in tasks),
            released_tasks=sum(item.status == PackagingTaskStatus.RELEASED_TO_STOCK for item in tasks),
            open_handling_units=sum(item.status == HandlingUnitStatus.OPEN for item in units),
            held_handling_units=sum(item.status == HandlingUnitStatus.QUALITY_HOLD for item in units),
            planned_quantity=sum((item.planned_quantity for item in tasks), Decimal('0')),
            packed_quantity=sum((item.packed_quantity for item in tasks), Decimal('0')),
        )


packaging_service = PackagingService()
