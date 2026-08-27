from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.material.crud.material import material_repo
from backend.plugin.material.enums import CategoryStatus, MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, MaterialCategory, UnitOfMeasure
from backend.plugin.material.schema.material import (
    CategoryTreeNode,
    CreateCategoryParam,
    CreateMaterialParam,
    CreateUnitParam,
    UpdateCategoryParam,
    UpdateMaterialParam,
    UpdateUnitParam,
)
from backend.plugin.warehouse.enums import WarehouseStatus
from backend.plugin.warehouse.model import Warehouse
from backend.plugin.warehouse.service.warehouse_service import warehouse_service


class MaterialService:
    @staticmethod
    async def _require_category(db: AsyncSession, category_id: int, active_only: bool = True) -> MaterialCategory:
        category = await material_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='MATERIAL_CATEGORY_NOT_FOUND')
        if active_only and category.status != CategoryStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_CATEGORY_DISABLED')
        return category

    @staticmethod
    async def _require_unit(db: AsyncSession, unit_id: int, active_only: bool = True) -> UnitOfMeasure:
        unit = await material_repo.get_unit(db, unit_id)
        if not unit:
            raise errors.NotFoundError(msg='MATERIAL_UNIT_NOT_FOUND')
        if active_only and unit.status != UnitStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_UNIT_DISABLED')
        return unit

    @staticmethod
    async def _require_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse:
        warehouse = await warehouse_service.get_warehouse(db, warehouse_id)
        if warehouse.status != WarehouseStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_WAREHOUSE_DISABLED')
        return warehouse

    @staticmethod
    async def _category_descendant_ids(db: AsyncSession, category_id: int) -> set[int]:
        categories = list(await material_repo.list_categories(db, status=None))
        category_ids = {category.id for category in categories}
        if category_id not in category_ids:
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
    async def _material_related_maps(
        db: AsyncSession, materials: list[Material]
    ) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
        category_ids = {material.category_id for material in materials}
        unit_ids = {material.base_unit_id for material in materials}
        warehouse_ids = {
            material.default_warehouse_id for material in materials if material.default_warehouse_id is not None
        }
        categories = (
            await db.scalars(
                select(MaterialCategory).where(MaterialCategory.id.in_(category_ids))
            )
        ).all() if category_ids else []
        units = (await db.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids)))).all() if unit_ids else []
        warehouses = (
            await db.scalars(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
        ).all() if warehouse_ids else []
        return (
            {item.id: item.category_name for item in categories},
            {item.id: item.unit_code for item in units},
            {item.id: item.warehouse_name for item in warehouses},
        )

    @staticmethod
    def _material_item(
        material: Material,
        category_names: dict[int, str],
        unit_codes: dict[int, str],
        warehouse_names: dict[int, str],
    ) -> dict[str, Any]:
        return {
            'id': material.id,
            'material_code': material.material_code,
            'material_name': material.material_name,
            'material_short_name': material.material_short_name,
            'material_type': material.material_type,
            'category_id': material.category_id,
            'category_name': category_names.get(material.category_id),
            'base_unit_id': material.base_unit_id,
            'unit_code': unit_codes.get(material.base_unit_id),
            'specification': material.specification,
            'model': material.model,
            'status': material.status,
            'batch_control': material.batch_control,
            'serial_control': material.serial_control,
            'purchasable': material.purchasable,
            'producible': material.producible,
            'sellable': material.sellable,
            'quality_inspection_required': material.quality_inspection_required,
            'default_warehouse_id': material.default_warehouse_id,
            'warehouse_name': warehouse_names.get(material.default_warehouse_id),
            'shelf_life_days': material.shelf_life_days,
            'remark': material.remark,
            'created_time': material.created_time,
            'updated_time': material.updated_time,
        }

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[MaterialCategory]:
        return list(await material_repo.list_categories(db, status=None))

    @staticmethod
    async def get_category_tree(db: AsyncSession) -> list[CategoryTreeNode]:
        categories = await MaterialService.list_categories(db)
        children: dict[int | None, list[MaterialCategory]] = defaultdict(list)
        for category in categories:
            children[category.parent_id].append(category)

        def build(parent_id: int | None, path: set[int] | None = None) -> list[CategoryTreeNode]:
            current_path = path or set()
            nodes: list[CategoryTreeNode] = []
            for category in children[parent_id]:
                if category.id in current_path:
                    continue
                nodes.append(
                    CategoryTreeNode(
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
    async def create_category(db: AsyncSession, obj: CreateCategoryParam) -> MaterialCategory:
        if await material_repo.get_category_by_code(db, obj.category_code):
            raise errors.ConflictError(msg='MATERIAL_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            await MaterialService._require_category(db, obj.parent_id)
        return await material_repo.create_category(db, obj.model_dump())

    @staticmethod
    async def update_category(db: AsyncSession, category_id: int, obj: UpdateCategoryParam) -> MaterialCategory:
        category = await material_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='MATERIAL_CATEGORY_NOT_FOUND')
        if await material_repo.get_category_by_code(db, obj.category_code, exclude_id=category_id):
            raise errors.ConflictError(msg='MATERIAL_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            if obj.parent_id == category_id:
                raise errors.ConflictError(msg='MATERIAL_CATEGORY_CYCLE')
            await MaterialService._require_category(db, obj.parent_id)
            candidate = obj.parent_id
            seen: set[int] = set()
            while candidate is not None:
                if candidate in seen or candidate == category_id:
                    raise errors.ConflictError(msg='MATERIAL_CATEGORY_CYCLE')
                seen.add(candidate)
                parent = await material_repo.get_category(db, candidate)
                candidate = parent.parent_id if parent else None
        for key, value in obj.model_dump().items():
            setattr(category, key, value)
        return category

    @staticmethod
    async def create_unit(db: AsyncSession, obj: CreateUnitParam) -> UnitOfMeasure:
        if await material_repo.get_unit_by_code(db, obj.unit_code):
            raise errors.ConflictError(msg='MATERIAL_UNIT_CODE_EXISTS')
        return await material_repo.create_unit(db, obj.model_dump())

    @staticmethod
    async def update_unit(db: AsyncSession, unit_id: int, obj: UpdateUnitParam) -> UnitOfMeasure:
        unit = await material_repo.get_unit(db, unit_id)
        if not unit:
            raise errors.NotFoundError(msg='MATERIAL_UNIT_NOT_FOUND')
        if await material_repo.get_unit_by_code(db, obj.unit_code, exclude_id=unit_id):
            raise errors.ConflictError(msg='MATERIAL_UNIT_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(unit, key, value)
        return unit

    @staticmethod
    async def list_units(db: AsyncSession, active_only: bool = True) -> list[UnitOfMeasure]:
        return list(await material_repo.list_units(db, active_only=active_only))

    @staticmethod
    async def create_material(db: AsyncSession, obj: CreateMaterialParam) -> Material:
        if await material_repo.get_material_by_code(db, obj.material_code):
            raise errors.ConflictError(msg='MATERIAL_CODE_EXISTS')
        await MaterialService._require_category(db, obj.category_id)
        await MaterialService._require_unit(db, obj.base_unit_id)
        if obj.default_warehouse_id is not None:
            await MaterialService._require_warehouse(db, obj.default_warehouse_id)
        return await material_repo.create_material(db, obj.model_dump())

    @staticmethod
    async def update_material(db: AsyncSession, material_id: int, obj: UpdateMaterialParam) -> Material:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        # TODO: once BOM, inventory or other business references exist, lock material_code after first use.
        if await material_repo.get_material_by_code(db, obj.material_code, exclude_id=material_id):
            raise errors.ConflictError(msg='MATERIAL_CODE_EXISTS')
        await MaterialService._require_category(db, obj.category_id)
        await MaterialService._require_unit(db, obj.base_unit_id)
        if obj.default_warehouse_id is not None:
            await MaterialService._require_warehouse(db, obj.default_warehouse_id)
        for key, value in obj.model_dump().items():
            setattr(material, key, value)
        return material

    @staticmethod
    async def get_material(db: AsyncSession, material_id: int) -> dict[str, Any]:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        category_names, unit_codes, warehouse_names = await MaterialService._material_related_maps(db, [material])
        return MaterialService._material_item(material, category_names, unit_codes, warehouse_names)

    @staticmethod
    async def list_materials(
        db: AsyncSession,
        keyword: str | None,
        material_type: str | None,
        category_id: int | None,
        status: MaterialStatus | None,
        batch_control: bool | None,
        purchasable: bool | None,
        producible: bool | None,
        sellable: bool | None,
    ) -> dict[str, Any]:
        category_ids = await MaterialService._category_descendant_ids(db, category_id) if category_id else None
        statement = await material_repo.get_material_select(
            keyword=keyword,
            material_type=material_type,
            category_ids=category_ids,
            status=status,
            batch_control=batch_control,
            purchasable=purchasable,
            producible=producible,
            sellable=sellable,
        )
        page_data = await paging_data(db, statement)
        materials = list(page_data['items'])
        category_names, unit_codes, warehouse_names = await MaterialService._material_related_maps(db, materials)
        page_data['items'] = [
            MaterialService._material_item(material, category_names, unit_codes, warehouse_names)
            for material in materials
        ]
        return page_data

    @staticmethod
    async def update_material_status(db: AsyncSession, material_id: int, status: MaterialStatus) -> Material:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        material.status = status
        return material

    @staticmethod
    async def list_options(
        db: AsyncSession,
        keyword: str | None,
        material_type: str | None,
        purchasable: bool | None,
        producible: bool | None,
        sellable: bool | None,
    ) -> list[dict[str, Any]]:
        statement = await material_repo.get_material_select(
            keyword=keyword,
            material_type=material_type,
            status=MaterialStatus.ACTIVE,
            purchasable=purchasable,
            producible=producible,
            sellable=sellable,
        )
        materials = list((await db.scalars(statement.limit(100))).all())
        unit_codes = {}
        unit_ids = {material.base_unit_id for material in materials}
        if unit_ids:
            units = (await db.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids)))).all()
            unit_codes = {unit.id: unit.unit_code for unit in units}
        return [
            {
                'id': material.id,
                'code': material.material_code,
                'name': material.material_name,
                'specification': material.specification,
                'unit': unit_codes.get(material.base_unit_id, ''),
            }
            for material in materials
        ]

    @staticmethod
    async def list_warehouse_options(db: AsyncSession) -> list[Warehouse]:
        warehouses = await warehouse_service.list_warehouses(db, keyword=None, warehouse_type=None, status='ACTIVE')
        return list(warehouses)


material_service = MaterialService()
