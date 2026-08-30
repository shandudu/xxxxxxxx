"""Validate shelf-life alerts, FEFO shipment, isolation disposition and recall in MySQL."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.inventory.enums import (
    ExpiryAlertLevel,
    LotHoldReason,
    LotHoldStatus,
    RecallItemStatus,
    RecallItemType,
    StockTransactionType,
)
from backend.plugin.inventory.model import InventoryBalance, LotQualityHold
from backend.plugin.inventory.schema.shelf_life import (
    CreateLotRecall,
    ReleaseLotHold,
    ScrapLotHold,
    ShelfLifePolicyUpsert,
    UpdateRecallItem,
)
from backend.plugin.inventory.service import inventory_service, shelf_life_service
from backend.plugin.quality.enums import InspectionResult
from backend.plugin.quality.schema.quality import CompleteInspection
from backend.plugin.quality.service import quality_service
from backend.plugin.sales.schema.sales import (
    CreateSalesOrder,
    CreateSalesOrderLine,
    CreateShipment,
    CreateShipmentLine,
)
from backend.plugin.sales.service import sales_service
from backend.plugin.trace.enums import LotSourceType, LotStatus, LotType, QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.utils.timezone import timezone


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                data = await demo_service._ensure_master_data(db)
                material = data['finished']
                warehouse = data['warehouse']
                location = data['location']
                customer = data['customer']
                now = timezone.now()
                run_key = uuid4().hex[:8].upper()

                lots = {
                    'expired_release': MaterialLot(
                        lot_no=f'FEFO-EXP-REL-{run_key}', material_id=material.id,
                        lot_type=LotType.FINISHED, source_type=LotSourceType.MANUAL,
                        production_date=now - timedelta(days=40), expiry_date=now - timedelta(days=1),
                        quantity=Decimal('2'), unit_id=material.base_unit_id,
                        quality_status=QualityStatus.PASS,
                    ),
                    'expired_scrap': MaterialLot(
                        lot_no=f'FEFO-EXP-SCR-{run_key}', material_id=material.id,
                        lot_type=LotType.FINISHED, source_type=LotSourceType.MANUAL,
                        production_date=now - timedelta(days=40), expiry_date=now - timedelta(days=2),
                        quantity=Decimal('1'), unit_id=material.base_unit_id,
                        quality_status=QualityStatus.PASS,
                    ),
                    'early': MaterialLot(
                        lot_no=f'FEFO-EARLY-{run_key}', material_id=material.id,
                        lot_type=LotType.FINISHED, source_type=LotSourceType.MANUAL,
                        production_date=now - timedelta(days=10), expiry_date=now + timedelta(days=10),
                        quantity=Decimal('3'), unit_id=material.base_unit_id,
                        quality_status=QualityStatus.PASS,
                    ),
                    'late': MaterialLot(
                        lot_no=f'FEFO-LATE-{run_key}', material_id=material.id,
                        lot_type=LotType.FINISHED, source_type=LotSourceType.MANUAL,
                        production_date=now - timedelta(days=5), expiry_date=now + timedelta(days=60),
                        quantity=Decimal('4'), unit_id=material.base_unit_id,
                        quality_status=QualityStatus.PASS,
                    ),
                }
                db.add_all(lots.values())
                await db.flush()
                for name, lot in lots.items():
                    await inventory_service.post_transaction(
                        db,
                        idempotency_key=f'FEFO-VALIDATE-RECEIPT:{run_key}:{name}',
                        transaction_type=StockTransactionType.RECEIPT,
                        material_id=material.id,
                        lot_id=lot.id,
                        warehouse_id=warehouse.id,
                        location_id=location.id,
                        quantity_delta=lot.quantity,
                        reference_type='FEFO_VALIDATION',
                        reference_no=run_key,
                    )

                await shelf_life_service.upsert_policy(
                    db,
                    material.id,
                    ShelfLifePolicyUpsert(
                        warning_days=30,
                        critical_days=7,
                        min_remaining_days_at_issue=1,
                    ),
                )
                alerts = await shelf_life_service.sync_expiry_alerts(db)
                expired_ids = {row.lot_id for row in alerts if row.level == ExpiryAlertLevel.EXPIRED}
                if expired_ids != {lots['expired_release'].id, lots['expired_scrap'].id}:
                    raise RuntimeError(f'expiry alert mismatch: {expired_ids}')

                try:
                    await inventory_service.post_transaction(
                        db,
                        idempotency_key=f'FEFO-VALIDATE-BLOCK:{run_key}',
                        transaction_type=StockTransactionType.ISSUE,
                        material_id=material.id,
                        lot_id=lots['expired_release'].id,
                        warehouse_id=warehouse.id,
                        location_id=location.id,
                        quantity_delta=Decimal('-1'),
                        reference_type='FEFO_VALIDATION',
                        reference_no=run_key,
                    )
                except errors.ConflictError as exc:
                    if exc.msg not in {'LOT_ISOLATED_OR_INACTIVE', 'LOT_QUALITY_HOLD_ACTIVE', 'LOT_EXPIRED'}:
                        raise
                else:
                    raise RuntimeError('expired lot was allowed to issue')

                candidates = await shelf_life_service.fefo_candidates(
                    db, material_id=material.id, warehouse_id=warehouse.id, quantity=Decimal('5')
                )
                if [(row.lot_id, row.allocated_quantity) for row in candidates] != [
                    (lots['early'].id, Decimal('3')),
                    (lots['late'].id, Decimal('2')),
                ]:
                    raise RuntimeError('FEFO candidates were not allocated by earliest expiry')

                order = await sales_service.create_order(
                    db,
                    CreateSalesOrder(
                        sales_order_no=f'FEFO-SO-{run_key}',
                        customer_id=customer.id,
                        lines=[CreateSalesOrderLine(material_id=material.id, ordered_quantity=Decimal('5'))],
                    ),
                )
                await sales_service.transition(db, order.id, 'confirm')
                shipment = await sales_service.create_shipment(
                    db,
                    CreateShipment(
                        shipment_no=f'FEFO-SHP-{run_key}',
                        sales_order_id=order.id,
                        lines=[CreateShipmentLine(
                            sales_order_line_id=order.lines[0].id,
                            warehouse_id=warehouse.id,
                            quantity=Decimal('5'),
                            auto_fefo=True,
                        )],
                    ),
                )
                if [(line.lot_id, line.quantity) for line in shipment.lines] != [
                    (lots['early'].id, Decimal('3')),
                    (lots['late'].id, Decimal('2')),
                ]:
                    raise RuntimeError('sales shipment did not expand FEFO allocations')

                release_hold = await db.scalar(select(LotQualityHold).where(
                    LotQualityHold.lot_id == lots['expired_release'].id,
                    LotQualityHold.reason == LotHoldReason.EXPIRED,
                    LotQualityHold.status == LotHoldStatus.OPEN,
                ))
                await shelf_life_service.create_reinspection(db, release_hold.id)
                await quality_service.complete_inspection(
                    db,
                    release_hold.inspection_id,
                    CompleteInspection(
                        accepted_quantity=Decimal('2'), rejected_quantity=Decimal('0'),
                        result=InspectionResult.PASS, conclusion='效期稳定性复检通过',
                    ),
                )
                released = await shelf_life_service.release_hold(
                    db,
                    release_hold.id,
                    ReleaseLotHold(
                        new_expiry_date=now + timedelta(days=90),
                        decision_reason='质量复检通过，批准延长效期',
                    ),
                )
                if released.status != LotHoldStatus.RELEASED:
                    raise RuntimeError('expired lot was not released after passed retest')
                await shelf_life_service.ensure_lot_issuable(db, lots['expired_release'].id)

                scrap_hold = await db.scalar(select(LotQualityHold).where(
                    LotQualityHold.lot_id == lots['expired_scrap'].id,
                    LotQualityHold.reason == LotHoldReason.EXPIRED,
                    LotQualityHold.status == LotHoldStatus.OPEN,
                ))
                scrapped = await shelf_life_service.scrap_hold(
                    db, scrap_hold.id, ScrapLotHold(decision_reason='过期批次批准报废')
                )
                remaining_scrap = Decimal(await db.scalar(select(func.coalesce(func.sum(InventoryBalance.quantity), 0)).where(
                    InventoryBalance.lot_id == lots['expired_scrap'].id,
                    InventoryBalance.deleted == 0,
                )) or 0)
                if scrapped.status != LotHoldStatus.SCRAPPED or remaining_scrap != 0:
                    raise RuntimeError('expired lot scrap did not clear inventory')

                recall = await shelf_life_service.create_recall(
                    db,
                    CreateLotRecall(
                        recall_no=f'FEFO-RECALL-{run_key}',
                        root_lot_id=lots['late'].id,
                        reason='模拟客户侧质量风险召回',
                        severity='CRITICAL',
                    ),
                )
                item_types = {item.item_type for item in recall.items}
                if item_types != {RecallItemType.INVENTORY_LOT, RecallItemType.SHIPMENT}:
                    raise RuntimeError(f'recall impact expansion mismatch: {item_types}')
                for item in recall.items:
                    await shelf_life_service.update_recall_item(
                        db,
                        recall.id,
                        item.id,
                        UpdateRecallItem(status=RecallItemStatus.CLOSED, action_notes='验证处置完成'),
                    )
                closed = await shelf_life_service.close_recall(db, recall.id)
                await db.refresh(lots['late'])
                if closed.status != 'CLOSED' or lots['late'].status != LotStatus.ACTIVE:
                    raise RuntimeError('recall close did not release resolved inventory lot')

                print(
                    'SHELF_LIFE_FEFO_RECALL_RUN_OK '
                    f'alerts={len(alerts)} allocations={len(shipment.lines)} '
                    f'recall_items={len(recall.items)} expired_blocked=True release=True scrap=True'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('SHELF_LIFE_FEFO_RECALL_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
