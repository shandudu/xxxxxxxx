from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.inventory.model import InventoryBalance, StockMovement, StockMovementLine, StockTransaction


class InventoryRepository:
    @staticmethod
    def balance_key(material_id: int, lot_id: int | None, warehouse_id: int, location_id: int) -> str:
        return f'{material_id}:{lot_id or 0}:{warehouse_id}:{location_id}'

    async def get_balance_for_update(
        self, db: AsyncSession, material_id: int, lot_id: int | None, warehouse_id: int, location_id: int
    ) -> InventoryBalance | None:
        key = self.balance_key(material_id, lot_id, warehouse_id, location_id)
        return await db.scalar(
            select(InventoryBalance).where(InventoryBalance.balance_key == key, InventoryBalance.deleted == 0).with_for_update()
        )

    async def list_balances(
        self, db: AsyncSession, material_id: int | None = None, warehouse_id: int | None = None,
        location_id: int | None = None, lot_id: int | None = None, positive_only: bool = False
    ) -> Sequence[InventoryBalance]:
        statement = select(InventoryBalance).where(InventoryBalance.deleted == 0)
        if material_id is not None:
            statement = statement.where(InventoryBalance.material_id == material_id)
        if warehouse_id is not None:
            statement = statement.where(InventoryBalance.warehouse_id == warehouse_id)
        if location_id is not None:
            statement = statement.where(InventoryBalance.location_id == location_id)
        if lot_id is not None:
            statement = statement.where(InventoryBalance.lot_id == lot_id)
        if positive_only:
            statement = statement.where(InventoryBalance.quantity > 0)
        return (await db.scalars(statement.order_by(InventoryBalance.material_id, InventoryBalance.location_id))).all()

    async def list_transactions(
        self, db: AsyncSession, material_id: int | None = None, lot_id: int | None = None,
        reference_type: str | None = None, reference_id: int | None = None, limit: int = 200
    ) -> Sequence[StockTransaction]:
        statement = select(StockTransaction)
        if material_id is not None:
            statement = statement.where(StockTransaction.material_id == material_id)
        if lot_id is not None:
            statement = statement.where(StockTransaction.lot_id == lot_id)
        if reference_type is not None:
            statement = statement.where(StockTransaction.reference_type == reference_type)
        if reference_id is not None:
            statement = statement.where(StockTransaction.reference_id == reference_id)
        return (await db.scalars(statement.order_by(StockTransaction.occurred_at.desc(), StockTransaction.id.desc()).limit(limit))).all()

    async def get_transaction_by_key(self, db: AsyncSession, key: str) -> StockTransaction | None:
        return await db.scalar(select(StockTransaction).where(StockTransaction.idempotency_key == key))

    async def get_movement(self, db: AsyncSession, movement_id: int, lock: bool = False) -> StockMovement | None:
        statement = select(StockMovement).where(StockMovement.id == movement_id, StockMovement.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def get_movement_by_no(self, db: AsyncSession, movement_no: str) -> StockMovement | None:
        return await db.scalar(select(StockMovement).where(StockMovement.movement_no == movement_no, StockMovement.deleted == 0))

    async def list_movements(self, db: AsyncSession, status: str | None = None) -> Sequence[StockMovement]:
        statement = select(StockMovement).where(StockMovement.deleted == 0)
        if status:
            statement = statement.where(StockMovement.status == status)
        return (await db.scalars(statement.order_by(StockMovement.created_time.desc(), StockMovement.id.desc()))).all()

    async def movement_lines(self, db: AsyncSession, movement_id: int) -> Sequence[StockMovementLine]:
        return (await db.scalars(select(StockMovementLine).where(
            StockMovementLine.movement_id == movement_id, StockMovementLine.deleted == 0
        ).order_by(StockMovementLine.line_no))).all()


inventory_repo = InventoryRepository()
