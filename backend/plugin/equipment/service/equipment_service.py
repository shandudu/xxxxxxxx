from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.equipment.crud.equipment import equipment_repo
from backend.plugin.equipment.enums import EquipmentCategoryStatus, EquipmentStatus, EquipmentType
from backend.plugin.equipment.model import Equipment, EquipmentCategory
from backend.plugin.equipment.schema.equipment import (
    CreateEquipmentCategoryParam,
    CreateEquipmentParam,
    EquipmentCategoryTreeNode,
    UpdateEquipmentCategoryParam,
    UpdateEquipmentParam,
)


class EquipmentService:
    @staticmethod
    async def _require_category(
        db: AsyncSession, category_id: int, active_only: bool = True
    ) -> EquipmentCategory:
        category = await equipment_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='EQUIPMENT_CATEGORY_NOT_FOUND')
        if active_only and category.status != EquipmentCategoryStatus.ACTIVE:
            raise errors.ConflictError(msg='EQUIPMENT_CATEGORY_DISABLED')
        return category

    @staticmethod
    async def _category_descendant_ids(db: AsyncSession, category_id: int) -> set[int]:
        categories = list(await equipment_repo.list_categories(db))
        if category_id not in {item.id for item in categories}:
            return set()
        children: dict[int | None, list[int]] = defaultdict(list)
        for category in categories:
            children[category.parent_id].append(category.id)

        result: set[int] = set()
        pending = [category_id]
        while pending:
            current = pending.pop()
            if current in result:
                continue
            result.add(current)
            pending.extend(children[current])
        return result

    @staticmethod
    async def _category_names(db: AsyncSession, equipment: list[Equipment]) -> dict[int, str]:
        category_ids = {item.category_id for item in equipment}
        if not category_ids:
            return {}
        categories = (
            await db.scalars(select(EquipmentCategory).where(EquipmentCategory.id.in_(category_ids)))
        ).all()
        return {item.id: item.category_name for item in categories}

    @staticmethod
    def _equipment_item(item: Equipment, category_names: dict[int, str]) -> dict[str, Any]:
        return {
            'id': item.id,
            'equipment_code': item.equipment_code,
            'equipment_name': item.equipment_name,
            'category_id': item.category_id,
            'category_name': category_names.get(item.category_id),
            'equipment_type': item.equipment_type,
            'model': item.model,
            'manufacturer': item.manufacturer,
            'serial_number': item.serial_number,
            'factory_code': item.factory_code,
            'area_code': item.area_code,
            'installation_location': item.installation_location,
            'status': item.status,
            'enabled': item.enabled,
            'production_enabled': item.production_enabled,
            'data_collection_enabled': item.data_collection_enabled,
            'maintenance_enabled': item.maintenance_enabled,
            'commission_date': item.commission_date,
            'service_date': item.service_date,
            'rated_capacity': item.rated_capacity,
            'capacity_unit': item.capacity_unit,
            'remark': item.remark,
            'created_time': item.created_time,
            'updated_time': item.updated_time,
        }

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[EquipmentCategory]:
        return list(await equipment_repo.list_categories(db))

    @staticmethod
    async def get_category_tree(db: AsyncSession) -> list[EquipmentCategoryTreeNode]:
        categories = await EquipmentService.list_categories(db)
        children: dict[int | None, list[EquipmentCategory]] = defaultdict(list)
        for category in categories:
            children[category.parent_id].append(category)

        def build(parent_id: int | None, path: set[int] | None = None) -> list[EquipmentCategoryTreeNode]:
            current_path = path or set()
            nodes: list[EquipmentCategoryTreeNode] = []
            for category in children[parent_id]:
                if category.id in current_path:
                    continue
                nodes.append(
                    EquipmentCategoryTreeNode(
                        id=category.id,
                        code=category.category_code,
                        name=category.category_name,
                        parent_id=category.parent_id,
                        status=category.status,
                        sort_no=category.sort_no,
                        remark=category.remark,
                        children=build(category.id, {*current_path, category.id}),
                    )
                )
            return nodes

        return build(None)

    @staticmethod
    async def create_category(
        db: AsyncSession, obj: CreateEquipmentCategoryParam
    ) -> EquipmentCategory:
        if await equipment_repo.get_category_by_code(db, obj.category_code):
            raise errors.ConflictError(msg='EQUIPMENT_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            await EquipmentService._require_category(db, obj.parent_id, active_only=False)
        return await equipment_repo.create_category(db, obj.model_dump())

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, obj: UpdateEquipmentCategoryParam
    ) -> EquipmentCategory:
        category = await equipment_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='EQUIPMENT_CATEGORY_NOT_FOUND')
        if await equipment_repo.get_category_by_code(db, obj.category_code, exclude_id=category_id):
            raise errors.ConflictError(msg='EQUIPMENT_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            if obj.parent_id == category_id:
                raise errors.ConflictError(msg='CATEGORY_CYCLE_DETECTED')
            await EquipmentService._require_category(db, obj.parent_id, active_only=False)
            candidate = obj.parent_id
            seen: set[int] = set()
            while candidate is not None:
                if candidate in seen or candidate == category_id:
                    raise errors.ConflictError(msg='CATEGORY_CYCLE_DETECTED')
                seen.add(candidate)
                parent = await equipment_repo.get_category(db, candidate)
                candidate = parent.parent_id if parent else None
        for key, value in obj.model_dump().items():
            setattr(category, key, value)
        return category

    @staticmethod
    async def create_equipment(db: AsyncSession, obj: CreateEquipmentParam) -> Equipment:
        if await equipment_repo.get_equipment_by_code(db, obj.equipment_code):
            raise errors.ConflictError(msg='EQUIPMENT_CODE_EXISTS')
        await EquipmentService._require_category(db, obj.category_id)
        data = obj.model_dump()
        data['status'] = EquipmentStatus.IDLE if obj.enabled else EquipmentStatus.DISABLED
        return await equipment_repo.create_equipment(db, data)

    @staticmethod
    async def update_equipment(
        db: AsyncSession, equipment_id: int, obj: UpdateEquipmentParam
    ) -> Equipment:
        equipment = await equipment_repo.get_equipment(db, equipment_id)
        if not equipment:
            raise errors.NotFoundError(msg='EQUIPMENT_NOT_FOUND')
        # TODO: lock equipment_code after the first production, maintenance, or quality business reference exists.
        if await equipment_repo.get_equipment_by_code(db, obj.equipment_code, exclude_id=equipment_id):
            raise errors.ConflictError(msg='EQUIPMENT_CODE_EXISTS')
        await EquipmentService._require_category(db, obj.category_id)
        for key, value in obj.model_dump().items():
            setattr(equipment, key, value)
        if not equipment.enabled:
            equipment.status = EquipmentStatus.DISABLED
        elif equipment.status == EquipmentStatus.DISABLED:
            equipment.status = EquipmentStatus.IDLE
        return equipment

    @staticmethod
    async def get_equipment(db: AsyncSession, equipment_id: int) -> dict[str, Any]:
        equipment = await equipment_repo.get_equipment(db, equipment_id)
        if not equipment:
            raise errors.NotFoundError(msg='EQUIPMENT_NOT_FOUND')
        data = EquipmentService._equipment_item(equipment, await EquipmentService._category_names(db, [equipment]))
        data['created_by'] = equipment.created_by
        data['updated_by'] = equipment.updated_by
        return data

    @staticmethod
    async def list_equipment(
        db: AsyncSession,
        keyword: str | None,
        category_id: int | None,
        equipment_type: EquipmentType | None,
        status: EquipmentStatus | None,
        enabled: bool | None,
        production_enabled: bool | None,
        data_collection_enabled: bool | None,
        maintenance_enabled: bool | None,
    ) -> dict[str, Any]:
        category_ids = await EquipmentService._category_descendant_ids(db, category_id) if category_id else None
        statement = await equipment_repo.get_equipment_select(
            keyword=keyword,
            category_ids=category_ids,
            equipment_type=equipment_type,
            status=status,
            enabled=enabled,
            production_enabled=production_enabled,
            data_collection_enabled=data_collection_enabled,
            maintenance_enabled=maintenance_enabled,
        )
        page_data = await paging_data(db, statement)
        items = list(page_data['items'])
        category_names = await EquipmentService._category_names(db, items)
        page_data['items'] = [EquipmentService._equipment_item(item, category_names) for item in items]
        return page_data

    @staticmethod
    async def update_enabled(db: AsyncSession, equipment_id: int, enabled: bool) -> Equipment:
        equipment = await equipment_repo.get_equipment(db, equipment_id)
        if not equipment:
            raise errors.NotFoundError(msg='EQUIPMENT_NOT_FOUND')
        equipment.enabled = enabled
        if not enabled:
            equipment.status = EquipmentStatus.DISABLED
        elif equipment.status == EquipmentStatus.DISABLED:
            equipment.status = EquipmentStatus.IDLE
        return equipment

    @staticmethod
    async def update_status(
        db: AsyncSession, equipment_id: int, status: EquipmentStatus
    ) -> Equipment:
        equipment = await equipment_repo.get_equipment(db, equipment_id)
        if not equipment:
            raise errors.NotFoundError(msg='EQUIPMENT_NOT_FOUND')
        if not equipment.enabled:
            raise errors.ConflictError(msg='EQUIPMENT_DISABLED')
        if status == EquipmentStatus.DISABLED:
            raise errors.ConflictError(msg='INVALID_EQUIPMENT_STATUS')
        equipment.status = status
        return equipment

    @staticmethod
    async def list_options(
        db: AsyncSession,
        keyword: str | None,
        equipment_type: EquipmentType | None,
        production_enabled: bool | None,
        maintenance_enabled: bool | None,
    ) -> list[dict[str, Any]]:
        statement = await equipment_repo.get_equipment_select(
            keyword=keyword,
            equipment_type=equipment_type,
            enabled=True,
            production_enabled=production_enabled,
            maintenance_enabled=maintenance_enabled,
        )
        items = list((await db.scalars(statement.limit(100))).all())
        return [
            {
                'id': item.id,
                'code': item.equipment_code,
                'name': item.equipment_name,
                'type': item.equipment_type,
                'status': item.status,
            }
            for item in items
        ]


equipment_service = EquipmentService()
