from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from fastapi.encoders import jsonable_encoder

from backend.common.context import ctx
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.material.enums import MaterialStatus, UnitStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.trace.enums import (
    LotSourceType,
    LotStatus,
    SerialStatus,
    TraceObjectType,
    TraceRelationType,
    TraceRuleStatus,
    TraceRuleType,
)
from backend.plugin.trace.generator.code_generator import trace_code_generator
from backend.plugin.trace.model import MaterialLot, MaterialSerial, MaterialTraceRule, TraceCodeRule, TraceRelation
from backend.plugin.trace.repository.trace import trace_repo
from backend.plugin.trace.schema.trace import (
    CreateMaterialLotParam,
    CreateTraceRelationParam,
    GenerateMaterialSerialParam,
    LotMergeParam,
    LotSplitParam,
    MaterialTraceRuleParam,
    TraceCodePreviewParam,
    TraceNode,
)


class TraceService:
    """Application service for code rules, lots, serials, and directed genealogy."""

    @staticmethod
    async def _require_material(db: AsyncSession, material_id: int, *, active_only: bool = True) -> Material:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if material is None:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if active_only and material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_DISABLED')
        return material

    @staticmethod
    async def _require_unit(db: AsyncSession, unit_id: int | None) -> UnitOfMeasure | None:
        if unit_id is None:
            return None
        unit = await db.scalar(select(UnitOfMeasure).where(UnitOfMeasure.id == unit_id, UnitOfMeasure.deleted == 0))
        if unit is None:
            raise errors.NotFoundError(msg='MATERIAL_UNIT_NOT_FOUND')
        if unit.status != UnitStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_UNIT_DISABLED')
        return unit

    @staticmethod
    async def _require_lot(db: AsyncSession, lot_id: int, *, active_only: bool = False) -> MaterialLot:
        lot = await trace_repo.get_lot(db, lot_id)
        if lot is None:
            raise errors.NotFoundError(msg='LOT_NOT_FOUND')
        if active_only and lot.status != LotStatus.ACTIVE:
            raise errors.ConflictError(msg='LOT_STATUS_INVALID')
        return lot

    @staticmethod
    async def _require_serial(db: AsyncSession, serial_id: int) -> MaterialSerial:
        serial = await trace_repo.get_serial(db, serial_id)
        if serial is None:
            raise errors.NotFoundError(msg='SERIAL_NOT_FOUND')
        return serial

    @staticmethod
    async def _require_rule(
        db: AsyncSession,
        rule_id: int,
        rule_type: TraceRuleType | None = None,
        *,
        active_only: bool = True,
    ) -> TraceCodeRule:
        rule = await trace_repo.get_rule(db, rule_id)
        if rule is None:
            raise errors.NotFoundError(msg='TRACE_RULE_NOT_FOUND')
        if rule_type is not None and rule.rule_type != rule_type:
            raise errors.ConflictError(msg='TRACE_RULE_TYPE_INVALID')
        if active_only and rule.status != TraceRuleStatus.ACTIVE:
            raise errors.ConflictError(msg='TRACE_RULE_DISABLED')
        return rule

    @staticmethod
    async def _get_material_rule(db: AsyncSession, material_id: int) -> MaterialTraceRule | None:
        return await trace_repo.get_material_rule(db, material_id)

    @staticmethod
    async def _rule_for_material(
        db: AsyncSession, material_id: int, rule_type: TraceRuleType
    ) -> TraceCodeRule:
        assignment = await TraceService._get_material_rule(db, material_id)
        rule_id = assignment.lot_rule_id if assignment and rule_type == TraceRuleType.LOT else None
        if assignment and rule_type == TraceRuleType.SERIAL:
            rule_id = assignment.serial_rule_id
        if rule_id is None:
            raise errors.NotFoundError(msg='TRACE_RULE_NOT_FOUND')
        return await TraceService._require_rule(db, rule_id, rule_type)

    @staticmethod
    def _rule_detail(rule: TraceCodeRule) -> dict[str, Any]:
        return {
            'id': rule.id,
            'rule_code': rule.rule_code,
            'rule_name': rule.rule_name,
            'rule_type': rule.rule_type,
            'pattern': rule.pattern,
            'sequence_length': rule.sequence_length,
            'sequence_reset_type': rule.sequence_reset_type,
            'prefix': rule.prefix,
            'status': rule.status,
            'example': rule.example,
            'remark': rule.remark,
            'created_time': rule.created_time,
            'updated_time': rule.updated_time,
        }

    @staticmethod
    async def _audit(
        db: AsyncSession,
        *,
        object_type: str,
        action: str,
        object_id: int | None = None,
        object_code: str | None = None,
        before_data: Any = None,
        after_data: Any = None,
    ) -> None:
        try:
            operator_id = ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            operator_id = None
        await trace_repo.create_operation_log(
            db,
            {
                'operator_id': operator_id,
                'object_type': object_type,
                'object_id': object_id,
                'object_code': object_code,
                'action': action,
                'before_data': jsonable_encoder(before_data) if before_data is not None else None,
                'after_data': jsonable_encoder(after_data) if after_data is not None else None,
            },
        )

    async def list_rules(self, db: AsyncSession, rule_type: TraceRuleType | None = None) -> list[dict[str, Any]]:
        rules = await trace_repo.list_rules(db, rule_type)
        return [self._rule_detail(rule) for rule in rules]

    async def create_rule(self, db: AsyncSession, data: dict[str, Any]) -> dict[str, Any]:
        trace_code_generator.validate_pattern(data['pattern'])
        if await trace_repo.get_rule_by_code(db, data['rule_code']):
            raise errors.ConflictError(msg='TRACE_RULE_CODE_EXISTS')
        rule = await trace_repo.create_rule(db, data)
        result = self._rule_detail(rule)
        await self._audit(
            db,
            object_type='TRACE_CODE_RULE',
            object_id=rule.id,
            object_code=rule.rule_code,
            action='CREATE',
            after_data=result,
        )
        return result

    async def update_rule(self, db: AsyncSession, rule_id: int, data: dict[str, Any]) -> dict[str, Any]:
        rule = await self._require_rule(db, rule_id, active_only=False)
        before_data = self._rule_detail(rule)
        trace_code_generator.validate_pattern(data['pattern'])
        if await trace_repo.get_rule_by_code(db, data['rule_code'], exclude_id=rule_id):
            raise errors.ConflictError(msg='TRACE_RULE_CODE_EXISTS')
        for key, value in data.items():
            setattr(rule, key, value)
        await db.flush()
        result = self._rule_detail(rule)
        await self._audit(
            db,
            object_type='TRACE_CODE_RULE',
            object_id=rule.id,
            object_code=rule.rule_code,
            action='UPDATE',
            before_data=before_data,
            after_data=result,
        )
        return result

    async def preview_rule(self, db: AsyncSession, obj: TraceCodePreviewParam) -> dict[str, str]:
        material = await self._require_material(db, obj.material_id, active_only=False) if obj.material_id else None
        example = await trace_code_generator.preview(
            obj.pattern,
            obj.sequence_length,
            material=material,
            prefix=obj.prefix,
        )
        return {'example': example}

    async def get_material_rule(self, db: AsyncSession, material_id: int) -> dict[str, Any]:
        await self._require_material(db, material_id, active_only=False)
        assignment = await self._get_material_rule(db, material_id)
        if assignment is None:
            return {'id': None, 'material_id': material_id, 'lot_rule_id': None, 'serial_rule_id': None}
        return {
            'id': assignment.id,
            'material_id': assignment.material_id,
            'lot_rule_id': assignment.lot_rule_id,
            'serial_rule_id': assignment.serial_rule_id,
            'created_time': assignment.created_time,
            'updated_time': assignment.updated_time,
        }

    async def update_material_rule(
        self, db: AsyncSession, material_id: int, obj: MaterialTraceRuleParam
    ) -> dict[str, Any]:
        await self._require_material(db, material_id, active_only=False)
        before_data = await self.get_material_rule(db, material_id)
        if obj.lot_rule_id is not None:
            await self._require_rule(db, obj.lot_rule_id, TraceRuleType.LOT)
        if obj.serial_rule_id is not None:
            await self._require_rule(db, obj.serial_rule_id, TraceRuleType.SERIAL)
        assignment = await self._get_material_rule(db, material_id)
        if assignment is None:
            assignment = await trace_repo.create_material_rule(
                db,
                {'material_id': material_id, 'lot_rule_id': obj.lot_rule_id, 'serial_rule_id': obj.serial_rule_id},
            )
        else:
            assignment.lot_rule_id = obj.lot_rule_id
            assignment.serial_rule_id = obj.serial_rule_id
            await db.flush()
        result = await self.get_material_rule(db, material_id)
        await self._audit(
            db,
            object_type='MATERIAL_TRACE_RULE',
            object_id=material_id,
            object_code=str(material_id),
            action='UPDATE',
            before_data=before_data,
            after_data=result,
        )
        return result

    @staticmethod
    async def _lot_related_maps(
        db: AsyncSession, lots: Sequence[MaterialLot]
    ) -> tuple[dict[int, Material], dict[int, UnitOfMeasure]]:
        material_ids = {lot.material_id for lot in lots}
        unit_ids = {lot.unit_id for lot in lots if lot.unit_id is not None}
        materials = (
            await db.scalars(select(Material).where(Material.id.in_(material_ids), Material.deleted == 0))
        ).all() if material_ids else []
        units = (
            await db.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids), UnitOfMeasure.deleted == 0))
        ).all() if unit_ids else []
        return ({item.id: item for item in materials}, {item.id: item for item in units})

    @staticmethod
    def _lot_item(
        lot: MaterialLot, materials: dict[int, Material], units: dict[int, UnitOfMeasure], *, detail: bool = False
    ) -> dict[str, Any]:
        material = materials.get(lot.material_id)
        unit = units.get(lot.unit_id) if lot.unit_id is not None else None
        result: dict[str, Any] = {
            'id': lot.id,
            'lot_no': lot.lot_no,
            'material_id': lot.material_id,
            'material_code': material.material_code if material else None,
            'material_name': material.material_name if material else None,
            'lot_type': lot.lot_type,
            'quantity': lot.quantity,
            'unit_id': lot.unit_id,
            'unit_code': unit.unit_code if unit else None,
            'status': lot.status,
            'quality_status': lot.quality_status,
            'production_date': lot.production_date,
            'expiry_date': lot.expiry_date,
            'created_time': lot.created_time,
            'updated_time': lot.updated_time,
        }
        if detail:
            result.update(
                {
                    'source_type': lot.source_type,
                    'source_ref_id': lot.source_ref_id,
                    'source_ref_no': lot.source_ref_no,
                    'parent_lot_id': lot.parent_lot_id,
                    'supplier_lot_no': lot.supplier_lot_no,
                    'remark': lot.remark,
                }
            )
        return result

    async def get_lot(self, db: AsyncSession, lot_id: int) -> dict[str, Any]:
        lot = await self._require_lot(db, lot_id)
        materials, units = await self._lot_related_maps(db, [lot])
        return self._lot_item(lot, materials, units, detail=True)

    async def list_lots(
        self, db: AsyncSession, keyword: str | None, material_id: int | None, status: LotStatus | None
    ) -> dict[str, Any]:
        statement = await trace_repo.lot_select(keyword, material_id, status)
        page_data = await paging_data(db, statement)
        lots = list(page_data['items'])
        materials, units = await self._lot_related_maps(db, lots)
        page_data['items'] = [self._lot_item(lot, materials, units) for lot in lots]
        return page_data

    async def create_lot(self, db: AsyncSession, obj: CreateMaterialLotParam) -> dict[str, Any]:
        material = await self._require_material(db, obj.material_id)
        if not material.batch_control:
            raise errors.ConflictError(msg='MATERIAL_BATCH_CONTROL_DISABLED')
        unit_id = obj.unit_id or material.base_unit_id
        await self._require_unit(db, unit_id)
        if obj.generate_by_rule:
            rule = await self._rule_for_material(db, material.id, TraceRuleType.LOT)
            lot_no = (await trace_code_generator.generate(db, rule, material, 1))[0]
        else:
            lot_no = obj.lot_no
        if lot_no is None:
            raise errors.RequestError(msg='LOT_CODE_REQUIRED')
        if await trace_repo.get_lot_by_no(db, lot_no):
            raise errors.ConflictError(msg='LOT_CODE_EXISTS')
        expiry_date = obj.expiry_date
        if expiry_date is None and obj.production_date is not None and material.shelf_life_days is not None:
            expiry_date = obj.production_date + timedelta(days=material.shelf_life_days)
        lot = await trace_repo.create_lot(
            db,
            {
                'lot_no': lot_no,
                'material_id': material.id,
                'lot_type': obj.lot_type,
                'source_type': obj.source_type,
                'source_ref_id': obj.source_ref_id,
                'source_ref_no': obj.source_ref_no,
                'production_date': obj.production_date,
                'expiry_date': expiry_date,
                'quantity': obj.quantity,
                'unit_id': unit_id,
                'status': obj.status,
                'quality_status': obj.quality_status,
                'supplier_lot_no': obj.supplier_lot_no,
                'remark': obj.remark,
            },
        )
        result = await self.get_lot(db, lot.id)
        await self._audit(
            db,
            object_type=TraceObjectType.LOT,
            object_id=lot.id,
            object_code=lot.lot_no,
            action='CREATE',
            after_data=result,
        )
        return result

    async def update_lot_status(self, db: AsyncSession, lot_id: int, status: LotStatus) -> dict[str, Any]:
        lot = await self._require_lot(db, lot_id)
        before_data = {'status': lot.status}
        lot.status = status
        await db.flush()
        result = await self.get_lot(db, lot.id)
        await self._audit(
            db,
            object_type=TraceObjectType.LOT,
            object_id=lot.id,
            object_code=lot.lot_no,
            action='STATUS_UPDATE',
            before_data=before_data,
            after_data={'status': lot.status},
        )
        return result

    @staticmethod
    def _business_ref_key(ref_type: str | None, ref_id: int | None, ref_no: str | None) -> str:
        return '|'.join((ref_type or '', str(ref_id) if ref_id is not None else '', ref_no or ''))

    @staticmethod
    def _relation_data(
        source_type: TraceObjectType,
        source_id: int,
        source_code: str,
        target_type: TraceObjectType,
        target_id: int,
        target_code: str,
        relation_type: TraceRelationType,
        *,
        quantity: Decimal | None = None,
        unit_id: int | None = None,
        operation_ref_id: int | None = None,
        business_ref_type: str | None = None,
        business_ref_id: int | None = None,
        business_ref_no: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        return {
            'source_type': source_type,
            'source_id': source_id,
            'source_code': source_code,
            'target_type': target_type,
            'target_id': target_id,
            'target_code': target_code,
            'relation_type': relation_type,
            'quantity': quantity,
            'unit_id': unit_id,
            'operation_ref_id': operation_ref_id,
            'business_ref_type': business_ref_type,
            'business_ref_id': business_ref_id,
            'business_ref_no': business_ref_no,
            'business_ref_key': TraceService._business_ref_key(business_ref_type, business_ref_id, business_ref_no),
            'remark': remark,
        }

    async def split_lot(self, db: AsyncSession, lot_id: int, obj: LotSplitParam) -> list[dict[str, Any]]:
        source = await self._require_lot(db, lot_id, active_only=True)
        if source.quantity is None:
            raise errors.ConflictError(msg='LOT_SPLIT_QUANTITY_INVALID')
        children_total = sum((child.quantity for child in obj.children), Decimal('0'))
        if children_total > source.quantity:
            raise errors.ConflictError(msg='LOT_SPLIT_QUANTITY_INVALID')
        for child in obj.children:
            if await trace_repo.get_lot_by_no(db, child.lot_no):
                raise errors.ConflictError(msg='LOT_CODE_EXISTS')

        children: list[MaterialLot] = []
        for child in obj.children:
            item = await trace_repo.create_lot(
                db,
                {
                    'lot_no': child.lot_no,
                    'material_id': source.material_id,
                    'lot_type': source.lot_type,
                    'source_type': LotSourceType.LOT_SPLIT,
                    'source_ref_id': source.id,
                    'source_ref_no': source.lot_no,
                    'parent_lot_id': source.id,
                    'production_date': source.production_date,
                    'expiry_date': source.expiry_date,
                    'quantity': child.quantity,
                    'unit_id': source.unit_id,
                    'quality_status': source.quality_status,
                    'supplier_lot_no': source.supplier_lot_no,
                    'remark': source.remark,
                },
            )
            children.append(item)
            await trace_repo.create_relation(
                db,
                self._relation_data(
                    TraceObjectType.LOT,
                    source.id,
                    source.lot_no,
                    TraceObjectType.LOT,
                    item.id,
                    item.lot_no,
                    TraceRelationType.SPLIT_TO,
                    quantity=item.quantity,
                    unit_id=item.unit_id,
                    business_ref_type=LotSourceType.LOT_SPLIT,
                    business_ref_id=source.id,
                    business_ref_no=source.lot_no,
                ),
            )
        materials, units = await self._lot_related_maps(db, children)
        result = [self._lot_item(item, materials, units, detail=True) for item in children]
        await self._audit(
            db,
            object_type=TraceObjectType.LOT,
            object_id=source.id,
            object_code=source.lot_no,
            action='SPLIT',
            after_data={'children': result},
        )
        return result

    async def merge_lots(self, db: AsyncSession, obj: LotMergeParam) -> dict[str, Any]:
        sources = [await self._require_lot(db, lot_id, active_only=True) for lot_id in obj.source_lot_ids]
        material_ids = {lot.material_id for lot in sources}
        if len(material_ids) != 1 or obj.target_lot.material_id not in material_ids:
            raise errors.ConflictError(msg='LOT_MERGE_MATERIAL_MISMATCH')
        if await trace_repo.get_lot_by_no(db, obj.target_lot.lot_no):
            raise errors.ConflictError(msg='LOT_CODE_EXISTS')
        material = await self._require_material(db, obj.target_lot.material_id)
        if not material.batch_control:
            raise errors.ConflictError(msg='MATERIAL_BATCH_CONTROL_DISABLED')
        unit_id = obj.target_lot.unit_id or material.base_unit_id
        await self._require_unit(db, unit_id)
        expiry_date = obj.target_lot.expiry_date
        if expiry_date is None and obj.target_lot.production_date and material.shelf_life_days is not None:
            expiry_date = obj.target_lot.production_date + timedelta(days=material.shelf_life_days)
        target = await trace_repo.create_lot(
            db,
            {
                'lot_no': obj.target_lot.lot_no,
                'material_id': material.id,
                'lot_type': obj.target_lot.lot_type,
                'source_type': LotSourceType.LOT_MERGE,
                'production_date': obj.target_lot.production_date,
                'expiry_date': expiry_date,
                'quantity': obj.target_lot.quantity,
                'unit_id': unit_id,
                'quality_status': obj.target_lot.quality_status,
                'remark': obj.target_lot.remark,
            },
        )
        for source in sources:
            await trace_repo.create_relation(
                db,
                self._relation_data(
                    TraceObjectType.LOT,
                    source.id,
                    source.lot_no,
                    TraceObjectType.LOT,
                    target.id,
                    target.lot_no,
                    TraceRelationType.MERGED_TO,
                    quantity=source.quantity,
                    unit_id=source.unit_id,
                    business_ref_type=LotSourceType.LOT_MERGE,
                    business_ref_id=target.id,
                    business_ref_no=target.lot_no,
                ),
            )
        result = await self.get_lot(db, target.id)
        await self._audit(
            db,
            object_type=TraceObjectType.LOT,
            object_id=target.id,
            object_code=target.lot_no,
            action='MERGE',
            before_data={'source_lot_ids': [source.id for source in sources]},
            after_data=result,
        )
        return result

    @staticmethod
    async def _serial_related_maps(
        db: AsyncSession, serials: Sequence[MaterialSerial]
    ) -> tuple[dict[int, Material], dict[int, MaterialLot]]:
        material_ids = {serial.material_id for serial in serials}
        lot_ids = {serial.lot_id for serial in serials if serial.lot_id is not None}
        materials = (
            await db.scalars(select(Material).where(Material.id.in_(material_ids), Material.deleted == 0))
        ).all() if material_ids else []
        lots = (
            await db.scalars(select(MaterialLot).where(MaterialLot.id.in_(lot_ids), MaterialLot.deleted == 0))
        ).all() if lot_ids else []
        return ({item.id: item for item in materials}, {item.id: item for item in lots})

    @staticmethod
    def _serial_item(
        serial: MaterialSerial, materials: dict[int, Material], lots: dict[int, MaterialLot], *, detail: bool = False
    ) -> dict[str, Any]:
        material = materials.get(serial.material_id)
        lot = lots.get(serial.lot_id) if serial.lot_id is not None else None
        result: dict[str, Any] = {
            'id': serial.id,
            'serial_no': serial.serial_no,
            'material_id': serial.material_id,
            'material_code': material.material_code if material else None,
            'material_name': material.material_name if material else None,
            'lot_id': serial.lot_id,
            'lot_no': lot.lot_no if lot else None,
            'status': serial.status,
            'quality_status': serial.quality_status,
            'production_date': serial.production_date,
            'created_time': serial.created_time,
            'updated_time': serial.updated_time,
        }
        if detail:
            result.update(
                {
                    'source_type': serial.source_type,
                    'source_ref_id': serial.source_ref_id,
                    'source_ref_no': serial.source_ref_no,
                    'remark': serial.remark,
                }
            )
        return result

    async def get_serial(self, db: AsyncSession, serial_id: int) -> dict[str, Any]:
        serial = await self._require_serial(db, serial_id)
        materials, lots = await self._serial_related_maps(db, [serial])
        return self._serial_item(serial, materials, lots, detail=True)

    async def list_serials(
        self,
        db: AsyncSession,
        keyword: str | None,
        material_id: int | None,
        lot_id: int | None,
        status: SerialStatus | None,
    ) -> dict[str, Any]:
        statement = await trace_repo.serial_select(keyword, material_id, lot_id, status)
        page_data = await paging_data(db, statement)
        serials = list(page_data['items'])
        materials, lots = await self._serial_related_maps(db, serials)
        page_data['items'] = [self._serial_item(serial, materials, lots) for serial in serials]
        return page_data

    async def generate_serials(self, db: AsyncSession, obj: GenerateMaterialSerialParam) -> list[str]:
        material = await self._require_material(db, obj.material_id)
        if not material.serial_control:
            raise errors.ConflictError(msg='MATERIAL_SERIAL_CONTROL_DISABLED')
        lot = None
        if obj.lot_id is not None:
            lot = await self._require_lot(db, obj.lot_id, active_only=True)
            if lot.material_id != material.id:
                raise errors.ConflictError(msg='SERIAL_LOT_MATERIAL_MISMATCH')
        rule = await self._rule_for_material(db, material.id, TraceRuleType.SERIAL)
        serial_numbers = await trace_code_generator.generate(db, rule, material, obj.quantity)
        serials = [
            MaterialSerial(
                serial_no=serial_no,
                material_id=material.id,
                lot_id=lot.id if lot else None,
                source_type=obj.source_type,
                source_ref_id=obj.source_ref_id,
                source_ref_no=obj.source_ref_no,
                production_date=obj.production_date,
                remark=obj.remark,
            )
            for serial_no in serial_numbers
        ]
        await trace_repo.create_serials(db, serials)
        if lot is not None:
            for serial in serials:
                await trace_repo.create_relation(
                    db,
                    self._relation_data(
                        TraceObjectType.LOT,
                        lot.id,
                        lot.lot_no,
                        TraceObjectType.SERIAL,
                        serial.id,
                        serial.serial_no,
                        TraceRelationType.PRODUCED_FROM,
                        business_ref_type='SERIAL_GENERATE',
                        business_ref_id=serial.id,
                        business_ref_no=serial.serial_no,
                    ),
                )
        await self._audit(
            db,
            object_type=TraceObjectType.SERIAL,
            object_id=lot.id if lot else material.id,
            object_code=lot.lot_no if lot else material.material_code,
            action='GENERATE',
            after_data={'count': len(serial_numbers), 'serials': serial_numbers[:100]},
        )
        return serial_numbers

    async def update_serial_status(self, db: AsyncSession, serial_id: int, status: SerialStatus) -> dict[str, Any]:
        serial = await self._require_serial(db, serial_id)
        before_data = {'status': serial.status}
        serial.status = status
        await db.flush()
        result = await self.get_serial(db, serial.id)
        await self._audit(
            db,
            object_type=TraceObjectType.SERIAL,
            object_id=serial.id,
            object_code=serial.serial_no,
            action='STATUS_UPDATE',
            before_data=before_data,
            after_data={'status': serial.status},
        )
        return result

    async def _trace_object(self, db: AsyncSession, object_type: TraceObjectType, object_id: int) -> MaterialLot | MaterialSerial:
        if object_type == TraceObjectType.LOT:
            return await self._require_lot(db, object_id)
        return await self._require_serial(db, object_id)

    async def _trace_object_by_code(
        self, db: AsyncSession, object_type: TraceObjectType, code: str
    ) -> MaterialLot | MaterialSerial:
        if object_type == TraceObjectType.LOT:
            item = await trace_repo.get_lot_by_no(db, code)
            if item is None:
                raise errors.NotFoundError(msg='LOT_NOT_FOUND')
            return item
        item = await trace_repo.get_serial_by_no(db, code)
        if item is None:
            raise errors.NotFoundError(msg='SERIAL_NOT_FOUND')
        return item

    @staticmethod
    def _object_code(item: MaterialLot | MaterialSerial) -> str:
        return item.lot_no if isinstance(item, MaterialLot) else item.serial_no

    async def _would_create_cycle(
        self,
        db: AsyncSession,
        source_type: TraceObjectType,
        source_id: int,
        target_type: TraceObjectType,
        target_id: int,
    ) -> bool:
        target_key = (target_type, target_id)
        source_key = (source_type, source_id)
        pending = [target_key]
        visited: set[tuple[TraceObjectType, int]] = set()
        while pending:
            current_type, current_id = pending.pop()
            current_key = (current_type, current_id)
            if current_key == source_key:
                return True
            if current_key in visited:
                continue
            visited.add(current_key)
            if len(visited) > 5000:
                raise errors.RequestError(msg='TRACE_RESULT_TOO_LARGE')
            relations = await trace_repo.outgoing_relations(db, current_type, current_id)
            pending.extend((relation.target_type, relation.target_id) for relation in relations)
        return False

    async def create_relation(self, db: AsyncSession, obj: CreateTraceRelationParam) -> dict[str, Any]:
        if obj.source_type == obj.target_type and obj.source_id == obj.target_id:
            raise errors.ConflictError(msg='TRACE_CYCLE_DETECTED')
        source = await self._trace_object(db, obj.source_type, obj.source_id)
        target = await self._trace_object(db, obj.target_type, obj.target_id)
        await self._require_material(db, source.material_id, active_only=False)
        await self._require_material(db, target.material_id, active_only=False)
        if obj.unit_id is not None:
            await self._require_unit(db, obj.unit_id)
        if obj.source_type == TraceObjectType.LOT and obj.target_type == TraceObjectType.SERIAL:
            if not isinstance(source, MaterialLot) or not isinstance(target, MaterialSerial):
                raise errors.RequestError(msg='TRACE_RELATION_INVALID')
            if target.lot_id != source.id or target.material_id != source.material_id:
                raise errors.ConflictError(msg='TRACE_RELATION_MATERIAL_INVALID')
        business_ref_key = self._business_ref_key(obj.business_ref_type, obj.business_ref_id, obj.business_ref_no)
        if await trace_repo.relation_exists(
            db,
            obj.source_type,
            obj.source_id,
            obj.target_type,
            obj.target_id,
            obj.relation_type,
            business_ref_key,
        ):
            raise errors.ConflictError(msg='TRACE_RELATION_EXISTS')
        if await self._would_create_cycle(db, obj.source_type, obj.source_id, obj.target_type, obj.target_id):
            raise errors.ConflictError(msg='TRACE_CYCLE_DETECTED')
        relation = await trace_repo.create_relation(
            db,
            self._relation_data(
                obj.source_type,
                obj.source_id,
                self._object_code(source),
                obj.target_type,
                obj.target_id,
                self._object_code(target),
                obj.relation_type,
                quantity=obj.quantity,
                unit_id=obj.unit_id,
                operation_ref_id=obj.operation_ref_id,
                business_ref_type=obj.business_ref_type,
                business_ref_id=obj.business_ref_id,
                business_ref_no=obj.business_ref_no,
                remark=obj.remark,
            ),
        )
        result = self._relation_detail(relation)
        await self._audit(
            db,
            object_type='TRACE_RELATION',
            object_id=relation.id,
            object_code=f'{relation.source_code}->{relation.target_code}',
            action='CREATE',
            after_data=result,
        )
        return result

    @staticmethod
    def _relation_detail(relation: TraceRelation) -> dict[str, Any]:
        return {
            'id': relation.id,
            'source_type': relation.source_type,
            'source_id': relation.source_id,
            'source_code': relation.source_code,
            'target_type': relation.target_type,
            'target_id': relation.target_id,
            'target_code': relation.target_code,
            'relation_type': relation.relation_type,
            'quantity': relation.quantity,
            'unit_id': relation.unit_id,
            'operation_ref_id': relation.operation_ref_id,
            'business_ref_type': relation.business_ref_type,
            'business_ref_id': relation.business_ref_id,
            'business_ref_no': relation.business_ref_no,
            'remark': relation.remark,
            'created_time': relation.created_time,
        }

    async def trace(
        self,
        db: AsyncSession,
        object_type: TraceObjectType,
        code: str,
        *,
        forward: bool,
        max_depth: int = 30,
    ) -> TraceNode:
        root = await self._trace_object_by_code(db, object_type, code.strip())
        material_cache: dict[int, Material | None] = {}
        node_count = 0

        async def make_node(
            current_type: TraceObjectType,
            current: MaterialLot | MaterialSerial,
            depth: int,
            path: set[tuple[TraceObjectType, int]],
            relation: TraceRelation | None = None,
        ) -> TraceNode:
            nonlocal node_count
            node_count += 1
            if node_count > 5000:
                raise errors.RequestError(msg='TRACE_RESULT_TOO_LARGE')
            material = material_cache.get(current.material_id)
            if current.material_id not in material_cache:
                material = await self._require_material(db, current.material_id, active_only=False)
                material_cache[current.material_id] = material
            current_key = (current_type, current.id)
            node = TraceNode(
                object_type=current_type,
                object_id=current.id,
                code=self._object_code(current),
                material_id=current.material_id,
                material_code=material.material_code if material else None,
                material_name=material.material_name if material else None,
                relation_type=relation.relation_type if relation else None,
                quantity=relation.quantity if relation else None,
                unit_id=relation.unit_id if relation else None,
            )
            if depth >= max_depth:
                return node
            relations = (
                await trace_repo.outgoing_relations(db, current_type, current.id)
                if forward
                else await trace_repo.incoming_relations(db, current_type, current.id)
            )
            children: list[TraceNode] = []
            for edge in relations:
                child_type = edge.target_type if forward else edge.source_type
                child_id = edge.target_id if forward else edge.source_id
                if (child_type, child_id) in path or (child_type, child_id) == current_key:
                    continue
                child = await self._trace_object(db, child_type, child_id)
                children.append(
                    await make_node(child_type, child, depth + 1, {*path, current_key}, relation=edge)
                )
            node.children = children
            return node

        return await make_node(object_type, root, 0, set())


trace_service = TraceService()
