from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom, BomItem
from backend.plugin.material.model import Material


class BomRepository:
    async def get(self, db: AsyncSession, bom_id: int) -> Bom | None:
        return await db.scalar(select(Bom).where(Bom.id == bom_id, Bom.deleted == 0))

    async def get_by_code(self, db: AsyncSession, bom_code: str, exclude_id: int | None = None) -> Bom | None:
        statement = select(Bom).where(Bom.bom_code == bom_code, Bom.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Bom.id != exclude_id)
        return await db.scalar(statement)

    async def get_by_product_version(
        self,
        db: AsyncSession,
        product_material_id: int,
        bom_version: str,
        exclude_id: int | None = None,
    ) -> Bom | None:
        statement = select(Bom).where(
            Bom.product_material_id == product_material_id,
            Bom.bom_version == bom_version,
            Bom.deleted == 0,
        )
        if exclude_id is not None:
            statement = statement.where(Bom.id != exclude_id)
        return await db.scalar(statement)

    async def create(self, db: AsyncSession, data: dict) -> Bom:
        bom = Bom(**data)
        db.add(bom)
        await db.flush()
        return bom

    async def update(self, bom: Bom, data: dict) -> Bom:
        for key, value in data.items():
            setattr(bom, key, value)
        return bom

    async def create_item(self, db: AsyncSession, data: dict) -> BomItem:
        item = BomItem(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_item(self, db: AsyncSession, bom_id: int, item_id: int) -> BomItem | None:
        return await db.scalar(
            select(BomItem).where(BomItem.id == item_id, BomItem.bom_id == bom_id, BomItem.deleted == 0)
        )

    async def get_item_by_line_no(
        self, db: AsyncSession, bom_id: int, line_no: int, exclude_id: int | None = None
    ) -> BomItem | None:
        statement = select(BomItem).where(
            BomItem.bom_id == bom_id,
            BomItem.line_no == line_no,
            BomItem.deleted == 0,
        )
        if exclude_id is not None:
            statement = statement.where(BomItem.id != exclude_id)
        return await db.scalar(statement)

    async def get_items(self, db: AsyncSession, bom_id: int) -> Sequence[BomItem]:
        statement = (
            select(BomItem)
            .where(BomItem.bom_id == bom_id, BomItem.deleted == 0)
            .order_by(BomItem.sort_no, BomItem.line_no, BomItem.id)
        )
        return (await db.scalars(statement)).all()

    async def get_all_items(self, db: AsyncSession) -> Sequence[BomItem]:
        statement = select(BomItem).where(BomItem.deleted == 0).order_by(BomItem.bom_id, BomItem.line_no)
        return (await db.scalars(statement)).all()

    async def get_all(self, db: AsyncSession, statuses: set[BomStatus] | None = None) -> Sequence[Bom]:
        statement = select(Bom).where(Bom.deleted == 0)
        if statuses:
            statement = statement.where(Bom.status.in_(statuses))
        return (await db.scalars(statement)).all()

    async def get_select(
        self,
        *,
        keyword: str | None = None,
        product_keyword: str | None = None,
        product_material_id: int | None = None,
        status: BomStatus | None = None,
        is_default: bool | None = None,
        effective_date=None,
    ) -> Select[tuple[Bom]]:
        statement: Select[tuple[Bom]] = select(Bom).where(Bom.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where((Bom.bom_code.ilike(like)) | (Bom.bom_version.ilike(like)))
        if product_material_id is not None:
            statement = statement.where(Bom.product_material_id == product_material_id)
        if product_keyword:
            product_like = f'%{product_keyword.strip()}%'
            statement = statement.join(Material, Bom.product_material_id == Material.id).where(
                Material.deleted == 0,
                (Material.material_code.ilike(product_like))
                | (Material.material_name.ilike(product_like))
                | Material.specification.ilike(product_like)
                | Material.model.ilike(product_like),
            )
        if status is not None:
            statement = statement.where(Bom.status == status)
        if is_default is not None:
            statement = statement.where(Bom.is_default == is_default)
        if effective_date is not None:
            statement = statement.where(
                Bom.effective_from.is_(None) | (Bom.effective_from <= effective_date),
                Bom.effective_to.is_(None) | (Bom.effective_to >= effective_date),
            )
        return statement.order_by(Bom.product_material_id, Bom.bom_version, Bom.id)


bom_repo = BomRepository()
