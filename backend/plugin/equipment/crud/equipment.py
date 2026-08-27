from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.equipment.enums import EquipmentCategoryStatus, EquipmentStatus, EquipmentType
from backend.plugin.equipment.model import Equipment, EquipmentCategory


class EquipmentRepository:
    async def get_category(self, db: AsyncSession, category_id: int) -> EquipmentCategory | None:
        return await db.scalar(
            select(EquipmentCategory).where(EquipmentCategory.id == category_id, EquipmentCategory.deleted == 0)
        )

    async def get_category_by_code(
        self, db: AsyncSession, code: str, exclude_id: int | None = None
    ) -> EquipmentCategory | None:
        statement = select(EquipmentCategory).where(
            EquipmentCategory.category_code == code, EquipmentCategory.deleted == 0
        )
        if exclude_id is not None:
            statement = statement.where(EquipmentCategory.id != exclude_id)
        return await db.scalar(statement)

    async def list_categories(
        self, db: AsyncSession, status: EquipmentCategoryStatus | None = None
    ) -> Sequence[EquipmentCategory]:
        statement = select(EquipmentCategory).where(EquipmentCategory.deleted == 0)
        if status is not None:
            statement = statement.where(EquipmentCategory.status == status)
        return (await db.scalars(statement.order_by(EquipmentCategory.sort_no, EquipmentCategory.id))).all()

    async def create_category(self, db: AsyncSession, data: dict) -> EquipmentCategory:
        category = EquipmentCategory(**data)
        db.add(category)
        await db.flush()
        return category

    async def get_equipment(self, db: AsyncSession, equipment_id: int) -> Equipment | None:
        return await db.scalar(select(Equipment).where(Equipment.id == equipment_id, Equipment.deleted == 0))

    async def get_equipment_by_code(
        self, db: AsyncSession, code: str, exclude_id: int | None = None
    ) -> Equipment | None:
        statement = select(Equipment).where(Equipment.equipment_code == code, Equipment.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Equipment.id != exclude_id)
        return await db.scalar(statement)

    async def create_equipment(self, db: AsyncSession, data: dict) -> Equipment:
        equipment = Equipment(**data)
        db.add(equipment)
        await db.flush()
        return equipment

    async def get_equipment_select(
        self,
        *,
        keyword: str | None = None,
        category_ids: set[int] | None = None,
        equipment_type: EquipmentType | None = None,
        status: EquipmentStatus | None = None,
        enabled: bool | None = None,
        production_enabled: bool | None = None,
        data_collection_enabled: bool | None = None,
        maintenance_enabled: bool | None = None,
    ) -> Select[tuple[Equipment]]:
        statement: Select[tuple[Equipment]] = select(Equipment).where(Equipment.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(
                Equipment.equipment_code.ilike(like)
                | Equipment.equipment_name.ilike(like)
                | Equipment.model.ilike(like)
                | Equipment.manufacturer.ilike(like)
                | Equipment.serial_number.ilike(like)
            )
        if category_ids:
            statement = statement.where(Equipment.category_id.in_(category_ids))
        if equipment_type is not None:
            statement = statement.where(Equipment.equipment_type == equipment_type)
        if status is not None:
            statement = statement.where(Equipment.status == status)
        if enabled is not None:
            statement = statement.where(Equipment.enabled == enabled)
        if production_enabled is not None:
            statement = statement.where(Equipment.production_enabled == production_enabled)
        if data_collection_enabled is not None:
            statement = statement.where(Equipment.data_collection_enabled == data_collection_enabled)
        if maintenance_enabled is not None:
            statement = statement.where(Equipment.maintenance_enabled == maintenance_enabled)
        return statement.order_by(Equipment.equipment_code, Equipment.id)


equipment_repo = EquipmentRepository()
