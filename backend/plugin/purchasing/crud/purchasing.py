from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.purchasing.model import PurchaseOrder, PurchaseOrderLine, SupplierReceipt, SupplierReceiptLine, SupplierReturn


class PurchasingRepository:
    async def list_orders(self, db: AsyncSession, supplier_id: int | None = None, status: str | None = None) -> Sequence[PurchaseOrder]:
        statement = select(PurchaseOrder).where(PurchaseOrder.deleted == 0)
        if supplier_id is not None:
            statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
        if status is not None:
            statement = statement.where(PurchaseOrder.status == status)
        return (await db.scalars(statement.order_by(PurchaseOrder.created_time.desc(), PurchaseOrder.id.desc()))).all()

    async def get_order(self, db: AsyncSession, order_id: int, lock: bool = False) -> PurchaseOrder | None:
        statement = select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def get_order_by_no(self, db: AsyncSession, number: str) -> PurchaseOrder | None:
        return await db.scalar(select(PurchaseOrder).where(PurchaseOrder.purchase_order_no == number, PurchaseOrder.deleted == 0))

    async def order_lines(self, db: AsyncSession, order_id: int, lock: bool = False) -> Sequence[PurchaseOrderLine]:
        statement = select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == order_id, PurchaseOrderLine.deleted == 0).order_by(PurchaseOrderLine.line_no)
        if lock:
            statement = statement.with_for_update()
        return (await db.scalars(statement)).all()

    async def get_order_line(self, db: AsyncSession, line_id: int, lock: bool = False) -> PurchaseOrderLine | None:
        statement = select(PurchaseOrderLine).where(PurchaseOrderLine.id == line_id, PurchaseOrderLine.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def list_receipts(self, db: AsyncSession, order_id: int | None = None) -> Sequence[SupplierReceipt]:
        statement = select(SupplierReceipt).where(SupplierReceipt.deleted == 0)
        if order_id is not None:
            statement = statement.where(SupplierReceipt.purchase_order_id == order_id)
        return (await db.scalars(statement.order_by(SupplierReceipt.created_time.desc(), SupplierReceipt.id.desc()))).all()

    async def get_receipt(self, db: AsyncSession, receipt_id: int) -> SupplierReceipt | None:
        return await db.scalar(select(SupplierReceipt).where(SupplierReceipt.id == receipt_id, SupplierReceipt.deleted == 0))

    async def get_receipt_by_no(self, db: AsyncSession, number: str) -> SupplierReceipt | None:
        return await db.scalar(select(SupplierReceipt).where(SupplierReceipt.receipt_no == number, SupplierReceipt.deleted == 0))

    async def receipt_lines(self, db: AsyncSession, receipt_id: int) -> Sequence[SupplierReceiptLine]:
        return (await db.scalars(select(SupplierReceiptLine).where(
            SupplierReceiptLine.supplier_receipt_id == receipt_id, SupplierReceiptLine.deleted == 0
        ).order_by(SupplierReceiptLine.line_no))).all()

    async def list_returns(self, db: AsyncSession, supplier_id: int | None = None) -> Sequence[SupplierReturn]:
        statement = select(SupplierReturn).where(SupplierReturn.deleted == 0)
        if supplier_id is not None:
            statement = statement.where(SupplierReturn.supplier_id == supplier_id)
        return (await db.scalars(statement.order_by(SupplierReturn.created_time.desc(), SupplierReturn.id.desc()))).all()


purchasing_repo = PurchasingRepository()
