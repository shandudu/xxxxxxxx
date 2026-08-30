from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.service import inventory_service
from backend.plugin.material.enums import MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.purchasing.crud import purchasing_repo
from backend.plugin.purchasing.enums import PurchaseOrderStatus
from backend.plugin.purchasing.model import PurchaseOrder, PurchaseOrderLine, SupplierReceipt, SupplierReceiptLine
from backend.plugin.purchasing.schema.purchasing import (
    CreatePurchaseOrder,
    ConfirmPurchaseOrder,
    CreateSupplierReceipt,
    PurchaseOrderDetail,
    PurchaseOrderLineDetail,
    SupplierReceiptDetail,
    SupplierReceiptLineDetail,
)
from backend.plugin.supplier.enums import CooperationStatus, SupplierStatus
from backend.plugin.supplier.model import Supplier
from backend.plugin.trace.enums import LotSourceType, LotType, QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.plugin.warehouse.model import Location, Warehouse
from backend.utils.timezone import timezone


class PurchasingService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def _require_supplier(db: AsyncSession, supplier_id: int) -> Supplier:
        supplier = await db.scalar(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted == 0))
        if not supplier:
            raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
        if supplier.status != SupplierStatus.ACTIVE or supplier.cooperation_status != CooperationStatus.NORMAL or not supplier.purchasing_enabled:
            raise errors.ConflictError(msg='SUPPLIER_NOT_PURCHASABLE')
        from backend.plugin.quality.service.sqm_service import sqm_service

        await sqm_service.ensure_supplier_purchasable(db, supplier.id)
        return supplier

    @staticmethod
    async def _material_and_unit(db: AsyncSession, material_id: int) -> tuple[Material, UnitOfMeasure]:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if material.status != MaterialStatus.ACTIVE or not material.purchasable:
            raise errors.ConflictError(msg='MATERIAL_NOT_PURCHASABLE')
        unit = await db.scalar(select(UnitOfMeasure).where(UnitOfMeasure.id == material.base_unit_id, UnitOfMeasure.deleted == 0))
        if not unit or unit.status != UnitStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_UNIT_UNAVAILABLE')
        return material, unit

    @staticmethod
    def _order_detail(order: PurchaseOrder, lines: Sequence[PurchaseOrderLine]) -> PurchaseOrderDetail:
        detail = PurchaseOrderDetail.model_validate(order)
        detail.lines = [PurchaseOrderLineDetail.model_validate(line) for line in lines]
        return detail

    @staticmethod
    def _receipt_detail(receipt: SupplierReceipt, lines: Sequence[SupplierReceiptLine]) -> SupplierReceiptDetail:
        detail = SupplierReceiptDetail.model_validate(receipt)
        detail.lines = [SupplierReceiptLineDetail.model_validate(line) for line in lines]
        return detail

    @staticmethod
    async def list_orders(db: AsyncSession, supplier_id: int | None = None, status: str | None = None) -> Sequence[PurchaseOrder]:
        return await purchasing_repo.list_orders(db, supplier_id, status)

    @staticmethod
    async def create_order(db: AsyncSession, obj: CreatePurchaseOrder) -> PurchaseOrderDetail:
        supplier = await PurchasingService._require_supplier(db, obj.supplier_id)
        number = (obj.purchase_order_no or f'PO-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await purchasing_repo.get_order_by_no(db, number):
            raise errors.ConflictError(msg='PURCHASE_ORDER_NO_EXISTS')
        order = PurchaseOrder(
            purchase_order_no=number, supplier_id=supplier.id,
            supplier_code_snapshot=supplier.supplier_code, supplier_name_snapshot=supplier.supplier_name,
            currency=obj.currency.upper(), remark=obj.remark,
        )
        db.add(order)
        await db.flush()
        lines: list[PurchaseOrderLine] = []
        for line_no, item in enumerate(obj.lines, start=1):
            material, unit = await PurchasingService._material_and_unit(db, item.material_id)
            from backend.plugin.supplier.service.lifecycle_service import supplier_lifecycle_service

            await supplier_lifecycle_service.ensure_supplier_material_approved(db, supplier.id, material.id)
            line = PurchaseOrderLine(
                purchase_order_id=order.id, line_no=line_no, material_id=material.id, unit_id=unit.id,
                ordered_quantity=item.ordered_quantity, unit_price=item.unit_price,
                requested_delivery_at=item.requested_delivery_at,
                material_code_snapshot=material.material_code, material_name_snapshot=material.material_name,
                unit_code_snapshot=unit.unit_code, unit_name_snapshot=unit.unit_name, remark=item.remark,
            )
            db.add(line)
            lines.append(line)
        await db.flush()
        return PurchasingService._order_detail(order, lines)

    @staticmethod
    async def get_order(db: AsyncSession, order_id: int) -> PurchaseOrderDetail:
        order = await purchasing_repo.get_order(db, order_id)
        if not order:
            raise errors.NotFoundError(msg='PURCHASE_ORDER_NOT_FOUND')
        return PurchasingService._order_detail(order, await purchasing_repo.order_lines(db, order.id))

    @staticmethod
    async def confirm_order(db: AsyncSession, order_id: int, obj: ConfirmPurchaseOrder | None = None) -> PurchaseOrderDetail:
        order = await purchasing_repo.get_order(db, order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='PURCHASE_ORDER_NOT_FOUND')
        if order.status == PurchaseOrderStatus.CONFIRMED:
            return await PurchasingService.get_order(db, order.id)
        if order.status != PurchaseOrderStatus.DRAFT:
            raise errors.ConflictError(msg='PURCHASE_ORDER_NOT_DRAFT')
        await PurchasingService._require_supplier(db, order.supplier_id)
        from backend.plugin.supplier.service.lifecycle_service import supplier_lifecycle_service

        for line in await purchasing_repo.order_lines(db, order.id, lock=True):
            await supplier_lifecycle_service.ensure_supplier_material_approved(db, order.supplier_id, line.material_id)
        order.status = PurchaseOrderStatus.CONFIRMED
        if obj and obj.supplier_confirmed_delivery_at:
            for line in await purchasing_repo.order_lines(db, order.id, lock=True):
                line.supplier_confirmed_delivery_at = obj.supplier_confirmed_delivery_at
        if obj and obj.remark:
            order.remark = obj.remark
        await db.flush()
        from backend.plugin.purchasing.service.supplier_delivery_service import supplier_delivery_service
        await supplier_delivery_service.refresh_order(db, order.id)
        return await PurchasingService.get_order(db, order.id)

    @staticmethod
    async def cancel_order(db: AsyncSession, order_id: int) -> PurchaseOrderDetail:
        order = await purchasing_repo.get_order(db, order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='PURCHASE_ORDER_NOT_FOUND')
        if order.status == PurchaseOrderStatus.CANCELLED:
            return await PurchasingService.get_order(db, order.id)
        if order.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CONFIRMED):
            raise errors.ConflictError(msg='RECEIVED_PURCHASE_ORDER_CANNOT_BE_CANCELLED')
        order.status = PurchaseOrderStatus.CANCELLED
        await db.flush()
        return await PurchasingService.get_order(db, order.id)

    @staticmethod
    async def _resolve_lot(db: AsyncSession, material: Material, item, receipt: SupplierReceipt) -> MaterialLot | None:
        if item.lot_id is not None:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == item.lot_id, MaterialLot.deleted == 0))
            if not lot:
                raise errors.NotFoundError(msg='LOT_NOT_FOUND')
            if lot.material_id != material.id:
                raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
            return lot
        if not item.lot_no:
            if material.batch_control:
                raise errors.RequestError(msg='LOT_REQUIRED')
            return None
        lot_no = item.lot_no.strip().upper()
        lot = await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == lot_no, MaterialLot.deleted == 0))
        if lot:
            if lot.material_id != material.id:
                raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
            return lot
        lot = MaterialLot(
            lot_no=lot_no, material_id=material.id, lot_type=LotType.SUPPLIER,
            source_type=LotSourceType.PURCHASE_RECEIPT, source_ref_id=receipt.id, source_ref_no=receipt.receipt_no,
            quantity=item.quantity, unit_id=material.base_unit_id,
            quality_status=QualityStatus.UNINSPECTED if material.quality_inspection_required else QualityStatus.PASS,
            supplier_lot_no=item.supplier_lot_no, remark=item.remark,
        )
        db.add(lot)
        await db.flush()
        return lot

    @staticmethod
    async def create_receipt(db: AsyncSession, obj: CreateSupplierReceipt) -> SupplierReceiptDetail:
        order = await purchasing_repo.get_order(db, obj.purchase_order_id, lock=True)
        if not order:
            raise errors.NotFoundError(msg='PURCHASE_ORDER_NOT_FOUND')
        if order.status not in (PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED):
            raise errors.ConflictError(msg='PURCHASE_ORDER_NOT_RECEIVABLE')
        number = (obj.receipt_no or f'RCV-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await purchasing_repo.get_receipt_by_no(db, number):
            raise errors.ConflictError(msg='SUPPLIER_RECEIPT_NO_EXISTS')
        receipt = SupplierReceipt(
            receipt_no=number, purchase_order_id=order.id, supplier_id=order.supplier_id,
            supplier_code_snapshot=order.supplier_code_snapshot, supplier_name_snapshot=order.supplier_name_snapshot,
            remark=obj.remark,
        )
        db.add(receipt)
        await db.flush()
        requested_ids = [item.purchase_order_line_id for item in obj.lines]
        if len(requested_ids) != len(set(requested_ids)):
            raise errors.RequestError(msg='DUPLICATE_PURCHASE_ORDER_LINE')
        receipt_lines: list[SupplierReceiptLine] = []
        for line_no, item in enumerate(obj.lines, start=1):
            order_line = await purchasing_repo.get_order_line(db, item.purchase_order_line_id, lock=True)
            if not order_line or order_line.purchase_order_id != order.id:
                raise errors.NotFoundError(msg='PURCHASE_ORDER_LINE_NOT_FOUND')
            remaining = order_line.ordered_quantity - order_line.received_quantity
            if item.quantity > remaining:
                raise errors.ConflictError(msg='RECEIPT_QUANTITY_EXCEEDS_REMAINING')
            material, _ = await PurchasingService._material_and_unit(db, order_line.material_id)
            warehouse = await db.scalar(select(Warehouse).where(Warehouse.id == item.warehouse_id, Warehouse.deleted == 0))
            location = await db.scalar(select(Location).where(Location.id == item.location_id, Location.deleted == 0))
            if not warehouse or not location:
                raise errors.NotFoundError(msg='RECEIPT_LOCATION_NOT_FOUND')
            if location.warehouse_id != warehouse.id:
                raise errors.ConflictError(msg='LOCATION_WAREHOUSE_MISMATCH')
            lot = await PurchasingService._resolve_lot(db, material, item, receipt)
            transaction = await inventory_service.post_transaction(
                db, idempotency_key=f'SUPPLIER_RECEIPT:{receipt.id}:{line_no}', transaction_type=StockTransactionType.RECEIPT,
                material_id=material.id, lot_id=lot.id if lot else None, warehouse_id=warehouse.id,
                location_id=location.id, quantity_delta=item.quantity, reference_type='SUPPLIER_RECEIPT',
                reference_id=receipt.id, reference_no=receipt.receipt_no, remark=item.remark,
                operator_id=PurchasingService._operator_id(),
            )
            receipt_line = SupplierReceiptLine(
                supplier_receipt_id=receipt.id, purchase_order_line_id=order_line.id, line_no=line_no,
                material_id=material.id, lot_id=lot.id if lot else None, warehouse_id=warehouse.id,
                location_id=location.id, quantity=item.quantity,
                material_code_snapshot=material.material_code, material_name_snapshot=material.material_name,
                lot_no_snapshot=lot.lot_no if lot else None, warehouse_code_snapshot=warehouse.warehouse_code,
                location_code_snapshot=location.location_code, stock_transaction_id=transaction.id, remark=item.remark,
            )
            db.add(receipt_line)
            await db.flush()

            # Keep the import local so the purchasing -> quality hook does not create a
            # module import cycle while still creating an IQC record when an active
            # incoming template exists.
            from backend.plugin.quality.service import quality_service

            if lot is not None:
                await quality_service.create_incoming_inspection(
                    db,
                    material_id=material.id,
                    lot=lot,
                    receipt=receipt,
                    quantity=item.quantity,
                )
            receipt_lines.append(receipt_line)
            order_line.received_quantity += item.quantity
        all_lines = await purchasing_repo.order_lines(db, order.id)
        order.status = (
            PurchaseOrderStatus.RECEIVED
            if all(line.received_quantity >= line.ordered_quantity for line in all_lines)
            else PurchaseOrderStatus.PARTIALLY_RECEIVED
        )
        await db.flush()
        from backend.plugin.purchasing.service.supplier_delivery_service import supplier_delivery_service
        await supplier_delivery_service.refresh_order(db, order.id)
        return PurchasingService._receipt_detail(receipt, receipt_lines)

    @staticmethod
    async def list_receipts(db: AsyncSession, order_id: int | None = None) -> Sequence[SupplierReceipt]:
        return await purchasing_repo.list_receipts(db, order_id)

    @staticmethod
    async def get_receipt(db: AsyncSession, receipt_id: int) -> SupplierReceiptDetail:
        receipt = await purchasing_repo.get_receipt(db, receipt_id)
        if not receipt:
            raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_NOT_FOUND')
        return PurchasingService._receipt_detail(receipt, await purchasing_repo.receipt_lines(db, receipt.id))

    @staticmethod
    async def list_returns(db: AsyncSession, supplier_id: int | None = None):
        return await purchasing_repo.list_returns(db, supplier_id)


purchasing_service = PurchasingService()
