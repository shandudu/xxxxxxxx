"""Validate repair-part idempotency scope and cost-posting freeze in MySQL."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import REFERENCES, SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.equipment.enums import EquipmentType
from backend.plugin.equipment.model import Equipment, EquipmentCategory
from backend.plugin.finance.model import FinancePeriod
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.service import inventory_service
from backend.plugin.maintenance.enums import (
    DowntimeCategory,
    DowntimeSourceType,
    DowntimeStatus,
    FaultLevel,
    RepairStatus,
)
from backend.plugin.maintenance.model import EquipmentDowntime, RepairCostPosting, RepairOrder
from backend.plugin.maintenance.schema.maintenance import IssueRepairPart
from backend.plugin.maintenance.service import maintenance_service
from backend.plugin.trace.model import MaterialLot
from backend.plugin.warehouse.model import Location, Warehouse
from backend.utils.timezone import timezone


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                lot = await db.scalar(
                    select(MaterialLot).where(
                        MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'],
                        MaterialLot.deleted == 0,
                    )
                )
                warehouse = await db.scalar(
                    select(Warehouse).where(
                        Warehouse.warehouse_code == REFERENCES['warehouse'], Warehouse.deleted == 0
                    )
                )
                location = await db.scalar(
                    select(Location).where(
                        Location.location_code == REFERENCES['location'], Location.deleted == 0
                    )
                )
                if not lot or not warehouse or not location:
                    raise RuntimeError('maintenance inventory references missing')
                await inventory_service.post_transaction(
                    db,
                    idempotency_key='REPAIR-FREEZE-STOCK',
                    transaction_type=StockTransactionType.RECEIPT,
                    material_id=lot.material_id,
                    lot_id=lot.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    quantity_delta=Decimal('2'),
                    reference_type='VALIDATION',
                    reference_no='REPAIR-FREEZE',
                )
                category = EquipmentCategory(
                    category_code='REPAIR-FREEZE-CAT', category_name='Repair freeze validation'
                )
                db.add(category)
                await db.flush()
                equipment = Equipment(
                    equipment_code='REPAIR-FREEZE-EQ',
                    equipment_name='Repair freeze validation',
                    category_id=category.id,
                    equipment_type=EquipmentType.PRODUCTION,
                )
                db.add(equipment)
                await db.flush()
                now = timezone.now()
                baseline_dashboard = await maintenance_service.dashboard(db)
                since = now - timedelta(days=30)
                db.add_all([
                    EquipmentDowntime(
                        downtime_no='REPAIR-FREEZE-DT-CLOSED',
                        equipment_id=equipment.id,
                        category=DowntimeCategory.UNPLANNED,
                        source_type=DowntimeSourceType.MANUAL,
                        start_at=since - timedelta(days=1),
                        end_at=since + timedelta(days=1),
                        status=DowntimeStatus.CLOSED,
                        duration_minutes=Decimal('2880'),
                    ),
                    EquipmentDowntime(
                        downtime_no='REPAIR-FREEZE-DT-OPEN',
                        equipment_id=equipment.id,
                        category=DowntimeCategory.UNPLANNED,
                        source_type=DowntimeSourceType.MANUAL,
                        start_at=since - timedelta(days=2),
                        status=DowntimeStatus.OPEN,
                    ),
                ])
                await db.flush()
                overlap_dashboard = await maintenance_service.dashboard(db)
                overlap_delta = (
                    overlap_dashboard.downtime_minutes_30d
                    - baseline_dashboard.downtime_minutes_30d
                )
                if abs(overlap_delta - Decimal('44640')) > Decimal('1'):
                    raise RuntimeError(f'maintenance 30d overlap calculation invalid: {overlap_delta}')
                repairs = [
                    RepairOrder(
                        repair_no=f'REPAIR-FREEZE-{index}',
                        equipment_id=equipment.id,
                        fault_level=FaultLevel.MINOR,
                        fault_description='validation',
                        reported_at=now,
                        status=RepairStatus.COMPLETED,
                        completed_at=now,
                    )
                    for index in (1, 2)
                ]
                db.add_all(repairs)
                await db.flush()
                request = IssueRepairPart(
                    material_id=lot.material_id,
                    lot_id=lot.id,
                    warehouse_id=warehouse.id,
                    location_id=location.id,
                    quantity=Decimal('1'),
                    unit_cost=Decimal('2'),
                    idempotency_key='shared-repair-part-key',
                )
                first = await maintenance_service.issue_repair_part(db, repairs[0].id, request)
                second = await maintenance_service.issue_repair_part(db, repairs[1].id, request)
                if first.id == second.id or first.repair_id == second.repair_id:
                    raise RuntimeError('repair-part idempotency key crossed repair orders')
                period = FinancePeriod(
                    period_code='REPAIR-FREEZE-PERIOD',
                    start_date=now.date(),
                    end_date=now.date() + timedelta(days=1),
                )
                db.add(period)
                await db.flush()
                db.add(
                    RepairCostPosting(
                        repair_id=repairs[0].id,
                        period_id=period.id,
                        posted_at=now,
                        parts_cost=first.total_cost,
                        total_cost=first.total_cost,
                    )
                )
                await db.flush()
                try:
                    await maintenance_service.issue_repair_part(
                        db,
                        repairs[0].id,
                        request.model_copy(update={'idempotency_key': 'post-cost-part-key'}),
                    )
                except errors.ConflictError as exc:
                    if exc.msg != 'REPAIR_COST_ALREADY_POSTED':
                        raise
                else:
                    raise RuntimeError('repair part was issued after cost posting')
                print(
                    'MAINTENANCE_COST_FREEZE_RUN_OK '
                    f'scoped_keys=2 blocked_after_posting=True overlap_minutes={overlap_delta}'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('MAINTENANCE_COST_FREEZE_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
