from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.trace.enums import LotStatus, SerialStatus, TraceObjectType
from backend.plugin.trace.model import (
    MaterialLot,
    MaterialSerial,
    MaterialTraceRule,
    TraceCodeRule,
    TraceCodeSequence,
    TraceOperationLog,
    TraceRelation,
)


class TraceRepository:
    async def get_rule(self, db: AsyncSession, rule_id: int) -> TraceCodeRule | None:
        return await db.scalar(select(TraceCodeRule).where(TraceCodeRule.id == rule_id, TraceCodeRule.deleted == 0))

    async def get_rule_by_code(
        self, db: AsyncSession, rule_code: str, exclude_id: int | None = None
    ) -> TraceCodeRule | None:
        statement = select(TraceCodeRule).where(TraceCodeRule.rule_code == rule_code, TraceCodeRule.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(TraceCodeRule.id != exclude_id)
        return await db.scalar(statement)

    async def list_rules(self, db: AsyncSession, rule_type: str | None = None) -> Sequence[TraceCodeRule]:
        statement = select(TraceCodeRule).where(TraceCodeRule.deleted == 0)
        if rule_type:
            statement = statement.where(TraceCodeRule.rule_type == rule_type)
        return (await db.scalars(statement.order_by(TraceCodeRule.rule_type, TraceCodeRule.rule_code))).all()

    async def create_rule(self, db: AsyncSession, data: dict) -> TraceCodeRule:
        item = TraceCodeRule(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_material_rule(self, db: AsyncSession, material_id: int) -> MaterialTraceRule | None:
        return await db.scalar(
            select(MaterialTraceRule).where(MaterialTraceRule.material_id == material_id, MaterialTraceRule.deleted == 0)
        )

    async def create_material_rule(self, db: AsyncSession, data: dict) -> MaterialTraceRule:
        item = MaterialTraceRule(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_lot(self, db: AsyncSession, lot_id: int, lock: bool = False) -> MaterialLot | None:
        statement = select(MaterialLot).where(MaterialLot.id == lot_id, MaterialLot.deleted == 0)
        if lock:
            statement = statement.with_for_update()
        return await db.scalar(statement)

    async def get_lot_by_no(self, db: AsyncSession, lot_no: str) -> MaterialLot | None:
        return await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == lot_no, MaterialLot.deleted == 0))

    async def create_lot(self, db: AsyncSession, data: dict) -> MaterialLot:
        item = MaterialLot(**data)
        db.add(item)
        await db.flush()
        return item

    async def lot_select(
        self,
        keyword: str | None = None,
        material_id: int | None = None,
        status: LotStatus | None = None,
    ) -> Select[tuple[MaterialLot]]:
        statement: Select[tuple[MaterialLot]] = select(MaterialLot).where(MaterialLot.deleted == 0)
        if keyword:
            statement = statement.where(MaterialLot.lot_no.ilike(f'%{keyword.strip()}%'))
        if material_id is not None:
            statement = statement.where(MaterialLot.material_id == material_id)
        if status is not None:
            statement = statement.where(MaterialLot.status == status)
        return statement.order_by(MaterialLot.created_time.desc(), MaterialLot.id.desc())

    async def get_serial(self, db: AsyncSession, serial_id: int) -> MaterialSerial | None:
        return await db.scalar(select(MaterialSerial).where(MaterialSerial.id == serial_id, MaterialSerial.deleted == 0))

    async def get_serial_by_no(self, db: AsyncSession, serial_no: str) -> MaterialSerial | None:
        return await db.scalar(select(MaterialSerial).where(MaterialSerial.serial_no == serial_no, MaterialSerial.deleted == 0))

    async def serial_select(
        self,
        keyword: str | None = None,
        material_id: int | None = None,
        lot_id: int | None = None,
        status: SerialStatus | None = None,
    ) -> Select[tuple[MaterialSerial]]:
        statement: Select[tuple[MaterialSerial]] = select(MaterialSerial).where(MaterialSerial.deleted == 0)
        if keyword:
            statement = statement.where(MaterialSerial.serial_no.ilike(f'%{keyword.strip()}%'))
        if material_id is not None:
            statement = statement.where(MaterialSerial.material_id == material_id)
        if lot_id is not None:
            statement = statement.where(MaterialSerial.lot_id == lot_id)
        if status is not None:
            statement = statement.where(MaterialSerial.status == status)
        return statement.order_by(MaterialSerial.created_time.desc(), MaterialSerial.id.desc())

    async def create_serials(self, db: AsyncSession, items: list[MaterialSerial]) -> list[MaterialSerial]:
        db.add_all(items)
        await db.flush()
        return items

    async def get_sequence_for_update(
        self, db: AsyncSession, rule_id: int, sequence_key: str
    ) -> TraceCodeSequence | None:
        return await db.scalar(
            select(TraceCodeSequence)
            .where(TraceCodeSequence.rule_id == rule_id, TraceCodeSequence.sequence_key == sequence_key)
            .with_for_update()
        )

    async def create_sequence(self, db: AsyncSession, rule_id: int, sequence_key: str, current_value: int) -> TraceCodeSequence:
        item = TraceCodeSequence(rule_id=rule_id, sequence_key=sequence_key, current_value=current_value)
        db.add(item)
        await db.flush()
        return item

    async def create_relation(self, db: AsyncSession, data: dict) -> TraceRelation:
        item = TraceRelation(**data)
        db.add(item)
        await db.flush()
        return item

    async def create_operation_log(self, db: AsyncSession, data: dict) -> TraceOperationLog:
        item = TraceOperationLog(**data)
        db.add(item)
        await db.flush()
        return item

    async def relation_exists(
        self,
        db: AsyncSession,
        source_type: TraceObjectType,
        source_id: int,
        target_type: TraceObjectType,
        target_id: int,
        relation_type: str,
        business_ref_key: str,
    ) -> bool:
        statement = select(TraceRelation.id).where(
            TraceRelation.deleted == 0,
            TraceRelation.source_type == source_type,
            TraceRelation.source_id == source_id,
            TraceRelation.target_type == target_type,
            TraceRelation.target_id == target_id,
            TraceRelation.relation_type == relation_type,
            TraceRelation.business_ref_key == business_ref_key,
        )
        return await db.scalar(statement) is not None

    async def outgoing_relations(
        self, db: AsyncSession, object_type: TraceObjectType, object_id: int
    ) -> Sequence[TraceRelation]:
        return (
            await db.scalars(
                select(TraceRelation)
                .where(
                    TraceRelation.deleted == 0,
                    TraceRelation.source_type == object_type,
                    TraceRelation.source_id == object_id,
                )
                .order_by(TraceRelation.id)
            )
        ).all()

    async def incoming_relations(
        self, db: AsyncSession, object_type: TraceObjectType, object_id: int
    ) -> Sequence[TraceRelation]:
        return (
            await db.scalars(
                select(TraceRelation)
                .where(
                    TraceRelation.deleted == 0,
                    TraceRelation.target_type == object_type,
                    TraceRelation.target_id == object_id,
                )
                .order_by(TraceRelation.id)
            )
        ).all()


trace_repo = TraceRepository()
