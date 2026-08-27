from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.maintenance.model import EquipmentDowntime, MaintenancePlan, MaintenanceTask, RepairOrder


class MaintenanceRepository:
    @staticmethod
    async def plans(db: AsyncSession) -> list[MaintenancePlan]:
        return list((await db.scalars(select(MaintenancePlan).where(MaintenancePlan.deleted == 0).order_by(MaintenancePlan.next_due_date, MaintenancePlan.plan_no))).all())

    @staticmethod
    async def tasks(db: AsyncSession) -> list[MaintenanceTask]:
        return list((await db.scalars(select(MaintenanceTask).where(MaintenanceTask.deleted == 0).order_by(MaintenanceTask.due_date.desc(), MaintenanceTask.id.desc()))).all())

    @staticmethod
    async def repairs(db: AsyncSession) -> list[RepairOrder]:
        return list((await db.scalars(select(RepairOrder).where(RepairOrder.deleted == 0).order_by(RepairOrder.reported_at.desc()))).all())

    @staticmethod
    async def downtimes(db: AsyncSession) -> list[EquipmentDowntime]:
        return list((await db.scalars(select(EquipmentDowntime).where(EquipmentDowntime.deleted == 0).order_by(EquipmentDowntime.start_at.desc()))).all())


maintenance_repository = MaintenanceRepository()
