from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.warehouse.model import Area, Location, Warehouse


class WarehouseRepository:
    async def get(self, db: AsyncSession, warehouse_id: int) -> Warehouse | None:
        return await db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.deleted == 0))

    async def list(
        self,
        db: AsyncSession,
        keyword: str | None = None,
        warehouse_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[Warehouse]:
        statement: Select[tuple[Warehouse]] = select(Warehouse).where(Warehouse.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(
                (Warehouse.warehouse_code.like(like)) | (Warehouse.warehouse_name.like(like))
            )
        if warehouse_type:
            statement = statement.where(Warehouse.warehouse_type == warehouse_type)
        if status:
            statement = statement.where(Warehouse.status == status)
        statement = statement.order_by(Warehouse.sort_no, Warehouse.id)
        return (await db.scalars(statement)).all()

    async def get_by_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> Warehouse | None:
        statement = select(Warehouse).where(Warehouse.warehouse_code == code, Warehouse.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Warehouse.id != exclude_id)
        return await db.scalar(statement)

    async def create(self, db: AsyncSession, data: dict) -> Warehouse:
        item = Warehouse(**data)
        db.add(item)
        await db.flush()
        return item

    async def update(self, item: Warehouse, data: dict) -> Warehouse:
        for key, value in data.items():
            setattr(item, key, value)
        return item

    async def area(self, db: AsyncSession, area_id: int) -> Area | None:
        return await db.scalar(select(Area).where(Area.id == area_id, Area.deleted == 0))

    async def areas(self, db: AsyncSession, warehouse_id: int) -> Sequence[Area]:
        statement = (
            select(Area)
            .where(Area.warehouse_id == warehouse_id, Area.deleted == 0)
            .order_by(Area.sort_no, Area.id)
        )
        return (await db.scalars(statement)).all()

    async def area_by_code(
        self, db: AsyncSession, warehouse_id: int, code: str, exclude_id: int | None = None
    ) -> Area | None:
        statement = select(Area).where(
            Area.warehouse_id == warehouse_id,
            Area.area_code == code,
            Area.deleted == 0,
        )
        if exclude_id is not None:
            statement = statement.where(Area.id != exclude_id)
        return await db.scalar(statement)

    async def create_area(self, db: AsyncSession, data: dict) -> Area:
        item = Area(**data)
        db.add(item)
        await db.flush()
        return item

    async def location(self, db: AsyncSession, location_id: int) -> Location | None:
        return await db.scalar(select(Location).where(Location.id == location_id, Location.deleted == 0))

    async def locations(
        self,
        db: AsyncSession,
        warehouse_id: int,
        area_id: int | None = None,
        keyword: str | None = None,
    ) -> Sequence[Location]:
        statement = select(Location).where(Location.warehouse_id == warehouse_id, Location.deleted == 0)
        if area_id is not None:
            statement = statement.where(Location.area_id == area_id)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(
                (Location.location_code.like(like)) | (Location.location_name.like(like))
            )
        statement = statement.order_by(Location.sort_no, Location.id)
        return (await db.scalars(statement)).all()

    async def location_by_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> Location | None:
        statement = select(Location).where(Location.location_code == code, Location.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Location.id != exclude_id)
        return await db.scalar(statement)

    async def create_location(self, db: AsyncSession, data: dict) -> Location:
        item = Location(**data)
        db.add(item)
        await db.flush()
        return item

    async def count_children(self, db: AsyncSession, parent_id: int) -> int:
        return int(
            await db.scalar(
                select(func.count(Location.id)).where(Location.parent_id == parent_id, Location.deleted == 0)
            )
            or 0
        )


warehouse_repo = WarehouseRepository()

