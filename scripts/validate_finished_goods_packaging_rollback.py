"""Validate the finished-goods packaging workflow against MySQL and roll it back."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select, text

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.inventory.model import StockTransaction
from backend.plugin.production.packaging_enums import HandlingUnitStatus, PackagingInspectionResult, PackagingTaskStatus
from backend.plugin.production.schema.packaging import (
    CreateHandlingUnit, CreatePackagingSpecification, CreatePackagingTask, InspectHandlingUnit,
    PrintPackagingLabel, RecordPackagingWeight, ScanPackagingItem, SealHandlingUnit,
)
from backend.plugin.production.schema.production import CreateProductionReport, CreateWorkOrder
from backend.plugin.production.service import packaging_service, production_service
from backend.plugin.trace.enums import QualityStatus
from backend.plugin.trace.model import MaterialLot


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                menu_permissions = (await db.execute(text(
                    "SELECT perms FROM sys_menu WHERE name IN "
                    "('MesPackaging','MesPackagingManage','MesPackagingExecute','MesPackagingInspect','MesPackagingRelease')"
                ))).scalars().all()
                tip_count = await db.scalar(text(
                    "SELECT COUNT(*) FROM sys_dict_data WHERE type_code='ui_tips' "
                    "AND value LIKE 'packaging.%' AND deleted=0"
                ))
                if len(menu_permissions) != 5 or tip_count != 10:
                    raise RuntimeError(
                        f'packaging migration metadata invalid: menu={len(menu_permissions)}, tips={tip_count}'
                    )
                data = await demo_service._ensure_master_data(db)
                bom, routing = await demo_service._ensure_definition(db, data)
                key = uuid4().hex[:8].upper()
                order = await production_service.create_order(db, CreateWorkOrder(
                    work_order_no=f'PKG-WO-{key}', product_material_id=data['finished'].id,
                    bom_id=bom.id, routing_id=routing.id, planned_quantity=Decimal('10'),
                ))
                await production_service.release_order(db, order.id)
                await production_service.start_order(db, order.id)
                report = await production_service.report_completion(db, CreateProductionReport(
                    report_no=f'PKG-RPT-{key}', idempotency_key=f'PKG-REPORT-{key}',
                    work_order_id=order.id, good_quantity=Decimal('10'), scrap_quantity=Decimal('0'),
                    warehouse_id=data['warehouse'].id, location_id=data['location'].id,
                    lot_no=f'PKG-LOT-{key}',
                ))
                lot = await db.get(MaterialLot, report.lot_id)
                lot.quality_status = QualityStatus.PASS
                spec = await packaging_service.create_specification(db, CreatePackagingSpecification(
                    spec_code=f'PKG-SPEC-{key}', spec_name='10 pcs weighted carton',
                    material_id=data['finished'].id, units_per_carton=Decimal('10'),
                    require_quality_release=True, require_weight_check=True,
                    target_gross_weight=Decimal('5'), weight_tolerance=Decimal('0.2'),
                    label_template_code='FG-CARTON-V1',
                ))
                task = await packaging_service.create_task(db, CreatePackagingTask(
                    production_report_id=report.id, specification_id=spec.id,
                    planned_quantity=Decimal('10'), idempotency_key=f'PKG-TASK-{key}',
                ))
                task = await packaging_service.create_task(db, CreatePackagingTask(
                    production_report_id=report.id, specification_id=spec.id,
                    planned_quantity=Decimal('10'), idempotency_key=f'PKG-TASK-{key}',
                ))
                await packaging_service.release_task(db, task.id)
                hu = await packaging_service.create_handling_unit(db, task.id, CreateHandlingUnit())
                hu = await packaging_service.scan_item(db, hu.id, ScanPackagingItem(
                    code=lot.lot_no, quantity=Decimal('10'), idempotency_key=f'PKG-SCAN-{key}',
                ))
                hu = await packaging_service.scan_item(db, hu.id, ScanPackagingItem(
                    code=lot.lot_no, quantity=Decimal('10'), idempotency_key=f'PKG-SCAN-{key}',
                ))
                weight = await packaging_service.record_weight(db, hu.id, RecordPackagingWeight(
                    gross_weight=Decimal('5.1'), tare_weight=Decimal('0.5'),
                    idempotency_key=f'PKG-WEIGHT-{key}',
                ))
                hu = await packaging_service.seal_handling_unit(db, hu.id, SealHandlingUnit())
                inspection = await packaging_service.inspect_handling_unit(db, hu.id, InspectHandlingUnit(
                    result=PackagingInspectionResult.PASS, idempotency_key=f'PKG-INSPECTION-{key}',
                ))
                await packaging_service.print_label(db, hu.id, PrintPackagingLabel(
                    idempotency_key=f'PKG-LABEL-{key}', copies=1,
                ))
                transaction_count_before = await db.scalar(select(func.count(StockTransaction.id)))
                task = await packaging_service.release_to_stock(db, task.id)
                transaction_count_after = await db.scalar(select(func.count(StockTransaction.id)))
                hu = await packaging_service.get_handling_unit(db, hu.hu_code)
                if task.status != PackagingTaskStatus.RELEASED_TO_STOCK:
                    raise RuntimeError(f'unexpected task status: {task.status}')
                if hu.status != HandlingUnitStatus.STORED or hu.quantity != Decimal('10'):
                    raise RuntimeError(f'unexpected HU result: {hu.status}/{hu.quantity}')
                if len(hu.contents) != 1 or weight.result != 'PASS' or inspection.result != 'PASS':
                    raise RuntimeError('idempotency, weight, or inspection validation failed')
                if task.stock_transaction_id != report.stock_transaction_id:
                    raise RuntimeError('packaging release did not preserve production stock transaction')
                if transaction_count_after != transaction_count_before:
                    raise RuntimeError('packaging release duplicated finished-goods inventory')
                print(
                    f'PACKAGING_RUN_OK task={task.task_no} hu={hu.hu_code} quantity={hu.quantity} '
                    f'weight={weight.result} inspection={inspection.result} stock_tx={task.stock_transaction_id}'
                )
                raise _RollbackValidation
        except _RollbackValidation:
            print('PACKAGING_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
