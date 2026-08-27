from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.inventory.crud import inventory_repo
from backend.plugin.inventory.enums import StockMovementStatus, StockTransactionType
from backend.plugin.inventory.model import InventoryBalance, StockMovement, StockMovementLine, StockTransaction
from backend.plugin.inventory.schema.inventory import CreateStockMovement, StockAdjustmentConfig, StockMovementDetail, StockMovementLineDetail
from backend.plugin.material.model import Material
from backend.plugin.trace.model import MaterialLot
from backend.plugin.warehouse.model import Location, Warehouse
from backend.utils.timezone import timezone


class InventoryService:
    @staticmethod
    async def _validate_position(
        db: AsyncSession, material_id: int, lot_id: int | None, warehouse_id: int, location_id: int
    ) -> None:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        warehouse = await db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.deleted == 0))
        if not warehouse:
            raise errors.NotFoundError(msg='WAREHOUSE_NOT_FOUND')
        location = await db.scalar(select(Location).where(Location.id == location_id, Location.deleted == 0))
        if not location:
            raise errors.NotFoundError(msg='LOCATION_NOT_FOUND')
        if location.warehouse_id != warehouse_id:
            raise errors.ConflictError(msg='LOCATION_WAREHOUSE_MISMATCH')
        if not location.storage_enabled:
            raise errors.ConflictError(msg='LOCATION_STORAGE_DISABLED')
        if lot_id is not None:
            lot = await db.scalar(select(MaterialLot).where(MaterialLot.id == lot_id, MaterialLot.deleted == 0))
            if not lot:
                raise errors.NotFoundError(msg='LOT_NOT_FOUND')
            if lot.material_id != material_id:
                raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
        elif material.batch_control:
            raise errors.RequestError(msg='LOT_REQUIRED')

    @staticmethod
    async def post_transaction(
        db: AsyncSession, *, idempotency_key: str, transaction_type: StockTransactionType,
        material_id: int, lot_id: int | None, warehouse_id: int, location_id: int,
        quantity_delta: Decimal, reference_type: str | None = None, reference_id: int | None = None,
        reference_no: str | None = None, remark: str | None = None, operator_id: int | None = None,
    ) -> StockTransaction:
        existing = await inventory_repo.get_transaction_by_key(db, idempotency_key)
        if existing:
            return existing
        if quantity_delta == 0:
            raise errors.RequestError(msg='ZERO_STOCK_TRANSACTION')
        await InventoryService._validate_position(db, material_id, lot_id, warehouse_id, location_id)
        balance = await inventory_repo.get_balance_for_update(db, material_id, lot_id, warehouse_id, location_id)
        if balance is None:
            balance = InventoryBalance(
                balance_key=inventory_repo.balance_key(material_id, lot_id, warehouse_id, location_id),
                material_id=material_id, lot_id=lot_id, warehouse_id=warehouse_id, location_id=location_id,
            )
            db.add(balance)
            await db.flush()
        next_quantity = balance.quantity + quantity_delta
        if next_quantity < 0:
            raise errors.ConflictError(msg='INSUFFICIENT_STOCK')
        if next_quantity < balance.reserved_quantity:
            raise errors.ConflictError(msg='QUANTITY_BELOW_RESERVED')
        balance.quantity = next_quantity
        balance.version += 1
        transaction = StockTransaction(
            transaction_no=f'STX-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}',
            idempotency_key=idempotency_key,
            transaction_type=transaction_type,
            material_id=material_id,
            lot_id=lot_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity_delta=quantity_delta,
            balance_after=next_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_no=reference_no,
            remark=remark,
            operator_id=operator_id,
        )
        db.add(transaction)
        await db.flush()
        return transaction

    @staticmethod
    async def list_balances(db: AsyncSession, **filters) -> Sequence[InventoryBalance]:
        return await inventory_repo.list_balances(db, **filters)

    @staticmethod
    async def list_transactions(db: AsyncSession, **filters) -> Sequence[StockTransaction]:
        return await inventory_repo.list_transactions(db, **filters)

    @staticmethod
    async def create_movement(db: AsyncSession, obj: CreateStockMovement) -> StockMovementDetail:
        movement_no = (obj.movement_no or f'MOV-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await inventory_repo.get_movement_by_no(db, movement_no):
            raise errors.ConflictError(msg='MOVEMENT_NO_EXISTS')
        movement = StockMovement(movement_no=movement_no, remark=obj.remark)
        db.add(movement)
        await db.flush()
        lines: list[StockMovementLine] = []
        for line_no, line_obj in enumerate(obj.lines, start=1):
            await InventoryService._validate_position(db, line_obj.material_id, line_obj.lot_id, line_obj.from_warehouse_id, line_obj.from_location_id)
            await InventoryService._validate_position(db, line_obj.material_id, line_obj.lot_id, line_obj.to_warehouse_id, line_obj.to_location_id)
            line = StockMovementLine(movement_id=movement.id, line_no=line_no, **line_obj.model_dump())
            db.add(line)
            lines.append(line)
        await db.flush()
        return StockMovementDetail.model_validate(movement).model_copy(update={'lines': lines})

    @staticmethod
    async def list_movements(db: AsyncSession, status: str | None = None) -> list[StockMovementDetail]:
        result = []
        for movement in await inventory_repo.list_movements(db, status):
            detail = StockMovementDetail.model_validate(movement)
            detail.lines = [StockMovementLineDetail.model_validate(line) for line in await inventory_repo.movement_lines(db, movement.id)]
            result.append(detail)
        return result

    @staticmethod
    async def get_movement(db: AsyncSession, movement_id: int) -> StockMovementDetail:
        movement = await inventory_repo.get_movement(db, movement_id)
        if not movement:
            raise errors.NotFoundError(msg='MOVEMENT_NOT_FOUND')
        lines = list(await inventory_repo.movement_lines(db, movement.id))
        return StockMovementDetail.model_validate(movement).model_copy(update={'lines': lines})

    @staticmethod
    async def post_movement(db: AsyncSession, movement_id: int, operator_id: int | None = None) -> StockMovementDetail:
        movement = await inventory_repo.get_movement(db, movement_id, lock=True)
        if not movement:
            raise errors.NotFoundError(msg='MOVEMENT_NOT_FOUND')
        if movement.status == StockMovementStatus.POSTED:
            return await InventoryService.get_movement(db, movement.id)
        if movement.status != StockMovementStatus.DRAFT:
            raise errors.ConflictError(msg='MOVEMENT_NOT_DRAFT')
        lines = list(await inventory_repo.movement_lines(db, movement.id))
        if not lines:
            raise errors.ConflictError(msg='MOVEMENT_HAS_NO_LINES')
        for line in lines:
            await InventoryService.post_transaction(
                db, idempotency_key=f'MOVEMENT:{movement.id}:{line.id}:OUT', transaction_type=StockTransactionType.TRANSFER_OUT,
                material_id=line.material_id, lot_id=line.lot_id, warehouse_id=line.from_warehouse_id,
                location_id=line.from_location_id, quantity_delta=-line.quantity, reference_type='STOCK_MOVEMENT',
                reference_id=movement.id, reference_no=movement.movement_no, remark=line.remark, operator_id=operator_id,
            )
            await InventoryService.post_transaction(
                db, idempotency_key=f'MOVEMENT:{movement.id}:{line.id}:IN', transaction_type=StockTransactionType.TRANSFER_IN,
                material_id=line.material_id, lot_id=line.lot_id, warehouse_id=line.to_warehouse_id,
                location_id=line.to_location_id, quantity_delta=line.quantity, reference_type='STOCK_MOVEMENT',
                reference_id=movement.id, reference_no=movement.movement_no, remark=line.remark, operator_id=operator_id,
            )
        movement.status = StockMovementStatus.POSTED
        movement.posted_at = timezone.now()
        movement.posted_by = operator_id
        await db.flush()
        return StockMovementDetail.model_validate(movement).model_copy(update={'lines': lines})

    @staticmethod
    async def post_adjustment(db: AsyncSession, obj: StockAdjustmentConfig, operator_id: int | None = None) -> StockTransaction:
        return await InventoryService.post_transaction(
            db, idempotency_key=f'ADJUSTMENT:{obj.idempotency_key}', transaction_type=StockTransactionType.ADJUSTMENT,
            material_id=obj.material_id, lot_id=obj.lot_id, warehouse_id=obj.warehouse_id,
            location_id=obj.location_id, quantity_delta=obj.quantity_delta, reference_type='STOCK_ADJUSTMENT',
            reference_no=obj.reference_no, remark=obj.remark, operator_id=operator_id,
        )


inventory_service = InventoryService()
