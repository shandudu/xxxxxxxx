from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.scheduling.model import ApsDispatch, ApsSchedule, Shift, WorkCalendar


class SchedulingRepository:
    @staticmethod
    async def shifts(db: AsyncSession) -> list[Shift]:
        return list((await db.scalars(select(Shift).where(Shift.deleted == 0).order_by(Shift.shift_code))).all())

    @staticmethod
    async def calendars(db: AsyncSession) -> list[WorkCalendar]:
        return list(
            (await db.scalars(select(WorkCalendar).where(WorkCalendar.deleted == 0).order_by(WorkCalendar.calendar_code))).all()
        )

    @staticmethod
    async def schedules(db: AsyncSession) -> list[ApsSchedule]:
        return list(
            (await db.scalars(select(ApsSchedule).where(ApsSchedule.deleted == 0).order_by(ApsSchedule.created_time.desc()))).all()
        )

    @staticmethod
    async def dispatches(db: AsyncSession) -> list[ApsDispatch]:
        return list(
            (await db.scalars(select(ApsDispatch).where(ApsDispatch.deleted == 0).order_by(ApsDispatch.created_time.desc()))).all()
        )


scheduling_repository = SchedulingRepository()
