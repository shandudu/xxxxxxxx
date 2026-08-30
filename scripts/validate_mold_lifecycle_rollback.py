"""Validate mold mount -> production shots -> maintenance -> cavity quality -> cost with rollback."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.equipment.enums import EquipmentType, MoldMaintenanceStatus, MoldQualityResult, MoldStatus
from backend.plugin.equipment.model import Equipment, EquipmentCategory, MoldAsset, MoldMaintenanceOrder, MoldUsageRecord
from backend.plugin.equipment.schema.mold import (
    CompleteMoldMaintenance, CreateCavityQuality, CreateMold, MountMold, UnmountMold,
)
from backend.plugin.equipment.service.mold_service import mold_service
from backend.plugin.production.schema.production import CreateProductionReport, CreateWorkOrder
from backend.plugin.production.service import production_service


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                data = await demo_service._ensure_master_data(db)
                bom, routing = await demo_service._ensure_definition(db, data)
                key = uuid4().hex[:8].upper()
                category = EquipmentCategory(category_code=f'MOLD-{key}', category_name='Mold validation')
                db.add(category)
                await db.flush()
                tool = Equipment(
                    equipment_code=f'TOOL-{key}', equipment_name='Validation mold tool',
                    category_id=category.id, equipment_type=EquipmentType.TOOL,
                )
                machine = Equipment(
                    equipment_code=f'MACHINE-{key}', equipment_name='Validation molding machine',
                    category_id=category.id, equipment_type=EquipmentType.PRODUCTION,
                )
                db.add_all([tool, machine])
                await db.flush()
                mold = await mold_service.create_mold(db, CreateMold(
                    mold_code=f'MOLD-{key}', mold_name='Validation 2-cavity mold',
                    tool_equipment_id=tool.id, product_material_id=data['finished'].id,
                    mold_type='INJECTION', cavity_count=2, designed_life_shots=20,
                    maintenance_interval_shots=4, acquisition_cost=Decimal('1000'),
                ))
                order = await production_service.create_order(db, CreateWorkOrder(
                    work_order_no=f'MOLD-WO-{key}', product_material_id=data['finished'].id,
                    bom_id=bom.id, routing_id=routing.id, planned_quantity=Decimal('8'),
                ))
                await production_service.release_order(db, order.id)
                await production_service.start_order(db, order.id)
                await mold_service.mount(db, mold.id, MountMold(equipment_id=machine.id, work_order_id=order.id))
                report = await production_service.report_completion(db, CreateProductionReport(
                    report_no=f'MOLD-RPT-{key}', idempotency_key=f'MOLD-REPORT-{key}',
                    work_order_id=order.id, good_quantity=Decimal('8'), scrap_quantity=Decimal('0'),
                    warehouse_id=data['warehouse'].id, location_id=data['location'].id,
                    lot_no=f'MOLD-LOT-{key}',
                ))
                usage = await db.scalar(select(MoldUsageRecord).where(MoldUsageRecord.production_report_id == report.id))
                asset = await db.scalar(select(MoldAsset).where(MoldAsset.id == mold.id))
                if not usage or usage.shot_count != 4 or asset.current_shots != 4:
                    raise RuntimeError('production report did not post four mold shots')
                await mold_service.register_report_usage(db, report)
                await db.refresh(asset)
                if asset.current_shots != 4:
                    raise RuntimeError('mold usage idempotency failed')
                auto_order = await db.scalar(select(MoldMaintenanceOrder).where(
                    MoldMaintenanceOrder.mold_id == mold.id,
                    MoldMaintenanceOrder.status == MoldMaintenanceStatus.PLANNED,
                ))
                if not auto_order:
                    raise RuntimeError('shot interval did not create maintenance order')
                await mold_service.unmount(db, mold.id, UnmountMold(remark='validation unmount'))
                await mold_service.start_maintenance(db, auto_order.id)
                await mold_service.complete_maintenance(db, auto_order.id, CompleteMoldMaintenance(
                    findings='Guide pin wear found', action_taken='Clean, lubricate, and replace guide pin',
                    labor_cost=Decimal('100'), material_cost=Decimal('50'), external_cost=Decimal('0'),
                ))
                cavities = await mold_service.list_cavities(db, mold.id)
                await mold_service.record_cavity_quality(db, mold.id, CreateCavityQuality(
                    cavity_id=cavities[0].id, inspected_quantity=Decimal('10'), defect_quantity=Decimal('1'),
                    result=MoldQualityResult.FAIL, defect_code='DIMENSION', notes='Cavity dimension out of tolerance',
                ))
                costs = await mold_service.cost_analysis(db, mold.id)
                await db.refresh(asset)
                if asset.shots_since_maintenance != 0 or asset.status != MoldStatus.AVAILABLE:
                    raise RuntimeError('maintenance did not reset mold availability and counter')
                if costs.total_lifecycle_cost != Decimal('1150') or costs.cost_per_shot != Decimal('287.5000'):
                    raise RuntimeError(f'unexpected mold costs: {costs}')
                repair = await db.scalar(select(MoldMaintenanceOrder).where(
                    MoldMaintenanceOrder.mold_id == mold.id,
                    MoldMaintenanceOrder.trigger_type == 'QUALITY',
                    MoldMaintenanceOrder.status == MoldMaintenanceStatus.PLANNED,
                ))
                if not repair:
                    raise RuntimeError('failed cavity quality did not create repair order')
                print(
                    'MOLD_LIFECYCLE_RUN_OK shots=4 idempotent=True maintenance=AUTO '
                    f'cavity=BLOCKED repair=PLANNED total_cost={costs.total_lifecycle_cost} '
                    f'cost_per_shot={costs.cost_per_shot}'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('MOLD_LIFECYCLE_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
