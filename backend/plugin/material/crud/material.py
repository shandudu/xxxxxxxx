from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.material.enums import CategoryStatus, MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, MaterialCategory, UnitOfMeasure


class MaterialRepository:
    async def get_category(self, db: AsyncSession, category_id: int) -> MaterialCategory | None:
        return await db.scalar(
            select(MaterialCategory).where(MaterialCategory.id == category_id, MaterialCategory.deleted == 0)
        )

    async def list_categories(
        self, db: AsyncSession, status: CategoryStatus | None = None
    ) -> Sequence[MaterialCategory]:
        statement = select(MaterialCategory).where(MaterialCategory.deleted == 0)
        if status is not None:
            statement = statement.where(MaterialCategory.status == status)
        statement = statement.order_by(MaterialCategory.sort_no, MaterialCategory.id)
        return (await db.scalars(statement)).all()

    async def get_category_by_code(
        self, db: AsyncSession, code: str, exclude_id: int | None = None
    ) -> MaterialCategory | None:
        statement = select(MaterialCategory).where(
            MaterialCategory.category_code == code,
            MaterialCategory.deleted == 0,
        )
        if exclude_id is not None:
            statement = statement.where(MaterialCategory.id != exclude_id)
        return await db.scalar(statement)

    async def create_category(self, db: AsyncSession, data: dict) -> MaterialCategory:
        category = MaterialCategory(**data)
        db.add(category)
        await db.flush()
        return category

    async def get_unit(self, db: AsyncSession, unit_id: int) -> UnitOfMeasure | None:
        return await db.scalar(select(UnitOfMeasure).where(UnitOfMeasure.id == unit_id, UnitOfMeasure.deleted == 0))

    async def list_units(self, db: AsyncSession, active_only: bool = True) -> Sequence[UnitOfMeasure]:
        statement = select(UnitOfMeasure).where(UnitOfMeasure.deleted == 0)
        if active_only:
            statement = statement.where(UnitOfMeasure.status == UnitStatus.ACTIVE)
        statement = statement.order_by(UnitOfMeasure.unit_code, UnitOfMeasure.id)
        return (await db.scalars(statement)).all()

    async def get_unit_by_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> UnitOfMeasure | None:
        statement = select(UnitOfMeasure).where(UnitOfMeasure.unit_code == code, UnitOfMeasure.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(UnitOfMeasure.id != exclude_id)
        return await db.scalar(statement)

    async def create_unit(self, db: AsyncSession, data: dict) -> UnitOfMeasure:
        unit = UnitOfMeasure(**data)
        db.add(unit)
        await db.flush()
        return unit

    async def get_material(self, db: AsyncSession, material_id: int) -> Material | None:
        return await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))

    async def get_material_by_code(
        self, db: AsyncSession, code: str, exclude_id: int | None = None
    ) -> Material | None:
        statement = select(Material).where(Material.material_code == code, Material.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Material.id != exclude_id)
        return await db.scalar(statement)

    async def create_material(self, db: AsyncSession, data: dict) -> Material:
        material = Material(**data)
        db.add(material)
        await db.flush()
        return material

    async def get_material_select(
        self,
        keyword: str | None = None,
        material_type: str | None = None,
        category_ids: set[int] | None = None,
        status: MaterialStatus | None = None,
        batch_control: bool | None = None,
        purchasable: bool | None = None,
        producible: bool | None = None,
        sellable: bool | None = None,
    ) -> Select[tuple[Material]]:
        statement: Select[tuple[Material]] = select(Material).where(Material.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(
                Material.material_code.ilike(like)
                | Material.material_name.ilike(like)
                | Material.material_short_name.ilike(like)
                | Material.specification.ilike(like)
                | Material.model.ilike(like)
            )
        if material_type:
            statement = statement.where(Material.material_type == material_type)
        if category_ids:
            statement = statement.where(Material.category_id.in_(category_ids))
        if status:
            statement = statement.where(Material.status == status)
        if batch_control is not None:
            statement = statement.where(Material.batch_control == batch_control)
        if purchasable is not None:
            statement = statement.where(Material.purchasable == purchasable)
        if producible is not None:
            statement = statement.where(Material.producible == producible)
        if sellable is not None:
            statement = statement.where(Material.sellable == sellable)
        return statement.order_by(Material.material_code, Material.id)


material_repo = MaterialRepository()
