from collections import defaultdict
from collections.abc import Sequence
from itertools import product
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.warehouse.crud.warehouse import warehouse_repo
from backend.plugin.warehouse.enums import AreaStatus, LocationStatus, WarehouseStatus
from backend.plugin.warehouse.model import Area, Location, Warehouse
from backend.plugin.warehouse.schema.warehouse import (
    CreateAreaConfig,
    CreateLocationConfig,
    CreateWarehouseConfig,
    LocationGenerateConfig,
    LocationMoveConfig,
    LocationStatusConfig,
    LocationGeneratePreview,
    TreeNode,
    UpdateAreaConfig,
    UpdateLocationConfig,
    UpdateWarehouseConfig,
    WarehouseTree,
)


class WarehouseService:
    @staticmethod
    async def list_warehouses(
        db: AsyncSession,
        keyword: str | None,
        warehouse_type: str | None,
        status: str | None,
    ) -> Sequence[Warehouse]:
        return await warehouse_repo.list(db, keyword, warehouse_type, status)

    @staticmethod
    async def get_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse:
        warehouse = await warehouse_repo.get(db, warehouse_id)
        if not warehouse:
            raise errors.NotFoundError(msg='Warehouse not found')
        return warehouse

    @staticmethod
    async def _require_active_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse:
        warehouse = await WarehouseService.get_warehouse(db, warehouse_id)
        if warehouse.status != WarehouseStatus.ACTIVE:
            raise errors.ConflictError(msg='Warehouse is disabled')
        return warehouse

    @staticmethod
    async def create_warehouse(db: AsyncSession, obj: CreateWarehouseConfig) -> Warehouse:
        if await warehouse_repo.get_by_code(db, obj.warehouse_code):
            raise errors.ConflictError(msg='WAREHOUSE_CODE_EXISTS')
        return await warehouse_repo.create(db, obj.model_dump())

    @staticmethod
    async def update_warehouse(db: AsyncSession, warehouse_id: int, obj: UpdateWarehouseConfig) -> Warehouse:
        warehouse = await WarehouseService.get_warehouse(db, warehouse_id)
        if await warehouse_repo.get_by_code(db, obj.warehouse_code, warehouse_id):
            raise errors.ConflictError(msg='WAREHOUSE_CODE_EXISTS')
        await warehouse_repo.update(warehouse, obj.model_dump())
        return warehouse

    @staticmethod
    async def list_areas(db: AsyncSession, warehouse_id: int) -> Sequence[Area]:
        await WarehouseService.get_warehouse(db, warehouse_id)
        return await warehouse_repo.areas(db, warehouse_id)

    @staticmethod
    async def get_area(db: AsyncSession, area_id: int) -> Area:
        area = await warehouse_repo.area(db, area_id)
        if not area:
            raise errors.NotFoundError(msg='Area not found')
        return area

    @staticmethod
    async def _require_active_area(db: AsyncSession, area_id: int) -> Area:
        area = await WarehouseService.get_area(db, area_id)
        await WarehouseService._require_active_warehouse(db, area.warehouse_id)
        if area.status != AreaStatus.ACTIVE:
            raise errors.ConflictError(msg='Area is disabled')
        return area

    @staticmethod
    async def create_area(db: AsyncSession, obj: CreateAreaConfig) -> Area:
        await WarehouseService._require_active_warehouse(db, obj.warehouse_id)
        if await warehouse_repo.area_by_code(db, obj.warehouse_id, obj.area_code):
            raise errors.ConflictError(msg='AREA_CODE_EXISTS')
        return await warehouse_repo.create_area(db, obj.model_dump())

    @staticmethod
    async def update_area(db: AsyncSession, area_id: int, obj: UpdateAreaConfig) -> Area:
        area = await WarehouseService.get_area(db, area_id)
        await WarehouseService._require_active_warehouse(db, obj.warehouse_id)
        if await warehouse_repo.area_by_code(db, obj.warehouse_id, obj.area_code, area_id):
            raise errors.ConflictError(msg='AREA_CODE_EXISTS')
        if area.warehouse_id != obj.warehouse_id:
            locations = await warehouse_repo.locations(db, area.warehouse_id, area.id)
            if locations:
                raise errors.ConflictError(msg='Area with locations cannot change warehouse')
        await warehouse_repo.update(area, obj.model_dump())
        return area

    @staticmethod
    async def list_locations(
        db: AsyncSession, warehouse_id: int, area_id: int | None, keyword: str | None
    ) -> Sequence[Location]:
        await WarehouseService.get_warehouse(db, warehouse_id)
        return await warehouse_repo.locations(db, warehouse_id, area_id, keyword)

    @staticmethod
    async def get_location(db: AsyncSession, location_id: int) -> Location:
        location = await warehouse_repo.location(db, location_id)
        if not location:
            raise errors.NotFoundError(msg='LOCATION_NOT_FOUND')
        return location

    @staticmethod
    async def _validate_location_parent(
        db: AsyncSession,
        warehouse_id: int,
        area_id: int,
        parent_id: int | None,
        current_id: int | None = None,
    ) -> None:
        area = await WarehouseService._require_active_area(db, area_id)
        if area.warehouse_id != warehouse_id:
            raise errors.ConflictError(msg='Area does not belong to warehouse')
        if parent_id is None:
            return
        parent = await WarehouseService.get_location(db, parent_id)
        if parent.warehouse_id != warehouse_id or parent.area_id != area_id:
            raise errors.ConflictError(msg='INVALID_LOCATION_PARENT')
        if parent.status != LocationStatus.AVAILABLE:
            raise errors.ConflictError(msg='Location parent is not available')
        if current_id is not None and parent.id == current_id:
            raise errors.ConflictError(msg='LOCATION_CYCLE_DETECTED')

    @staticmethod
    async def create_location(db: AsyncSession, obj: CreateLocationConfig) -> Location:
        await WarehouseService._validate_location_parent(db, obj.warehouse_id, obj.area_id, obj.parent_id)
        if await warehouse_repo.location_by_code(db, obj.location_code):
            raise errors.ConflictError(msg='LOCATION_CODE_EXISTS')
        return await warehouse_repo.create_location(db, obj.model_dump())

    @staticmethod
    async def update_location(db: AsyncSession, location_id: int, obj: UpdateLocationConfig) -> Location:
        location = await WarehouseService.get_location(db, location_id)
        await WarehouseService._validate_location_parent(
            db, obj.warehouse_id, obj.area_id, obj.parent_id, current_id=location_id
        )
        if await warehouse_repo.location_by_code(db, obj.location_code, location_id):
            raise errors.ConflictError(msg='LOCATION_CODE_EXISTS')
        await WarehouseService._ensure_not_descendant(db, location_id, obj.parent_id)
        await warehouse_repo.update(location, obj.model_dump())
        return location

    @staticmethod
    async def update_location_status(db: AsyncSession, location_id: int, obj: LocationStatusConfig) -> Location:
        location = await WarehouseService.get_location(db, location_id)
        if obj.status == LocationStatus.AVAILABLE:
            await WarehouseService._require_active_area(db, location.area_id)
        location.status = obj.status
        return location

    @staticmethod
    async def move_location(db: AsyncSession, location_id: int, obj: LocationMoveConfig) -> Location:
        location = await WarehouseService.get_location(db, location_id)
        await WarehouseService._validate_location_parent(
            db, location.warehouse_id, location.area_id, obj.target_parent_id, current_id=location_id
        )
        await WarehouseService._ensure_not_descendant(db, location_id, obj.target_parent_id)
        location.parent_id = obj.target_parent_id
        return location

    @staticmethod
    async def _ensure_not_descendant(db: AsyncSession, location_id: int, parent_id: int | None) -> None:
        candidate = parent_id
        seen: set[int] = set()
        while candidate is not None:
            if candidate in seen:
                raise errors.ConflictError(msg='LOCATION_CYCLE_DETECTED')
            seen.add(candidate)
            if candidate == location_id:
                raise errors.ConflictError(msg='LOCATION_CYCLE_DETECTED')
            parent = await warehouse_repo.location(db, candidate)
            if not parent:
                raise errors.NotFoundError(msg='INVALID_LOCATION_PARENT')
            candidate = parent.parent_id

    @staticmethod
    async def get_tree(db: AsyncSession, warehouse_id: int) -> WarehouseTree:
        warehouse = await WarehouseService.get_warehouse(db, warehouse_id)
        areas = list(await warehouse_repo.areas(db, warehouse_id))
        locations = list(await warehouse_repo.locations(db, warehouse_id))
        locations_by_parent: dict[int | None, list[Location]] = defaultdict(list)
        for location in locations:
            locations_by_parent[location.parent_id].append(location)

        def build_location(location: Location) -> TreeNode:
            return TreeNode(
                id=location.id,
                node_type=location.location_type,
                code=location.location_code,
                name=location.location_name,
                status=location.status,
                storage_enabled=location.storage_enabled,
                children=[build_location(item) for item in locations_by_parent[location.id]],
            )

        children: list[TreeNode] = []
        for area in areas:
            children.append(
                TreeNode(
                    id=area.id,
                    node_type='AREA',
                    code=area.area_code,
                    name=area.area_name,
                    status=area.status,
                    children=[build_location(item) for item in locations_by_parent[None] if item.area_id == area.id],
                )
            )
        return WarehouseTree(
            warehouse_id=warehouse.id,
            warehouse_code=warehouse.warehouse_code,
            warehouse_name=warehouse.warehouse_name,
            children=children,
        )

    @staticmethod
    async def search_locations(db: AsyncSession, warehouse_id: int, keyword: str) -> list[dict[str, Any]]:
        locations = list(await warehouse_repo.locations(db, warehouse_id, keyword=keyword))
        by_id = {location.id: location for location in locations}
        result = []
        for location in locations:
            path_ids = [location.id]
            path_names = [location.location_name]
            parent_id = location.parent_id
            while parent_id is not None:
                parent = by_id.get(parent_id) or await warehouse_repo.location(db, parent_id)
                if not parent:
                    break
                path_ids.insert(0, parent.id)
                path_names.insert(0, parent.location_name)
                parent_id = parent.parent_id
            result.append(
                {
                    'id': location.id,
                    'location_code': location.location_code,
                    'location_name': location.location_name,
                    'path_ids': path_ids,
                    'path': ' / '.join(path_names),
                }
            )
        return result

    @staticmethod
    def _format_location_code(obj: LocationGenerateConfig, rack: int, level: int, bin_no: int) -> str:
        try:
            return obj.pattern.format(
                AREA=obj.area_prefix,
                RACK=f'{rack:0{obj.rack.digits}d}',
                LEVEL=f'{level:0{obj.level.digits}d}',
                BIN=f'{bin_no:0{obj.bin.digits}d}',
            )
        except (KeyError, ValueError) as exc:
            raise errors.RequestError(msg='Invalid location code pattern') from exc

    @staticmethod
    async def _generate_codes(obj: LocationGenerateConfig) -> list[str]:
        codes = [
            WarehouseService._format_location_code(obj, rack, level, bin_no)
            for rack, level, bin_no in product(
                range(obj.rack.start, obj.rack.end + 1),
                range(obj.level.start, obj.level.end + 1),
                range(obj.bin.start, obj.bin.end + 1),
            )
        ]
        if len(codes) != len(set(codes)):
            raise errors.ConflictError(msg='Generated location codes contain duplicates')
        return codes

    @staticmethod
    async def preview_generate(db: AsyncSession, obj: LocationGenerateConfig) -> LocationGeneratePreview:
        await WarehouseService._validate_location_parent(db, obj.warehouse_id, obj.area_id, obj.parent_id)
        codes = await WarehouseService._generate_codes(obj)
        existing = set(
            await db.scalars(
                select(Location.location_code).where(
                    Location.location_code.in_(codes), Location.deleted == 0
                )
            )
        )
        return LocationGeneratePreview(count=len(codes), examples=codes[:20], conflicts=sorted(existing))

    @staticmethod
    async def generate_locations(db: AsyncSession, obj: LocationGenerateConfig) -> list[Location]:
        preview = await WarehouseService.preview_generate(db, obj)
        if preview.conflicts:
            raise errors.ConflictError(msg=f'LOCATION_CODE_EXISTS: {", ".join(preview.conflicts[:10])}')
        codes = await WarehouseService._generate_codes(obj)
        locations = []
        for code in codes:
            location = await warehouse_repo.create_location(
                db,
                {
                    'warehouse_id': obj.warehouse_id,
                    'area_id': obj.area_id,
                    'parent_id': obj.parent_id,
                    'location_code': code,
                    'location_name': obj.location_name_template or code,
                    'location_type': obj.location_type,
                    'location_level': 1,
                    'status': LocationStatus.AVAILABLE,
                    'storage_enabled': True,
                    'mixed_material_allowed': False,
                    'mixed_lot_allowed': False,
                    'sort_no': 0,
                },
            )
            locations.append(location)
        return locations


warehouse_service = WarehouseService()
