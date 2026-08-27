"""Exercise refund, replacement, repair and scrap execution orders and roll back by default."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.customer.model import Customer
from backend.plugin.demo.service.demo_service import SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.quality.enums import AfterSalesExecutionStatus, CustomerReturnResolution, InspectionResult
from backend.plugin.quality.model import CustomerAfterSalesAudit, CustomerAfterSalesRepairTask
from backend.plugin.quality.schema.quality import CompleteAfterSalesRepairTask, CompleteCustomerReturnInspection, CreateAfterSalesOrder, CreateCustomerComplaint, CreateCustomerReturn, ResolveCustomerReturn
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.sales.model import Shipment, ShipmentLine
from backend.plugin.trace.model import MaterialLot
from backend.plugin.warehouse.model import Location, Warehouse


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                customer = await db.scalar(select(Customer).where(Customer.customer_code == 'DEMO-CUS-001', Customer.deleted == 0))
                shipment = await db.scalar(select(Shipment).where(Shipment.shipment_no == SALES_ORDER_DRIVEN_REFERENCES['shipment'], Shipment.deleted == 0))
                lot = await db.scalar(select(MaterialLot).where(MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'], MaterialLot.deleted == 0))
                line = await db.scalar(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id, ShipmentLine.deleted == 0)) if shipment else None
                warehouse = await db.scalar(select(Warehouse).where(Warehouse.warehouse_code == 'DEMO-WH-001', Warehouse.deleted == 0))
                location = await db.scalar(select(Location).where(Location.location_code == 'DEMO-LOC-001', Location.deleted == 0))
                if not all((customer, shipment, lot, line, warehouse, location)):
                    raise RuntimeError('demo data missing')

                for index, resolution in enumerate((CustomerReturnResolution.REFUND, CustomerReturnResolution.REPLACEMENT, CustomerReturnResolution.REPAIR, CustomerReturnResolution.SCRAP), 1):
                    complaint = await quality_service.create_customer_complaint(db, CreateCustomerComplaint(customer_id=customer.id, shipment_id=shipment.id, material_id=line.material_id, lot_id=lot.id, quantity=Decimal('1'), title=f'售后处理验证 {resolution}', description='after-sales rollback validation'))
                    returned = await quality_service.create_customer_return(db, CreateCustomerReturn(complaint_id=complaint.id, shipment_id=shipment.id, lines=[{'shipment_line_id': line.id, 'material_id': line.material_id, 'lot_id': lot.id, 'warehouse_id': warehouse.id, 'location_id': location.id, 'quantity': Decimal('1')}]))
                    returned = await quality_service.receive_customer_return(db, returned.id)
                    returned = await quality_service.inspect_customer_return(db, returned.id, CompleteCustomerReturnInspection(line_id=returned.lines[0].id, accepted_quantity=Decimal('1'), rejected_quantity=Decimal('0'), result=InspectionResult.PASS, conclusion='退货检验合格'))
                    returned = await quality_service.resolve_customer_return(db, returned.id, ResolveCustomerReturn(resolution_type=resolution, resolution_notes='执行验证'))
                    order = await quality_service.create_after_sales_order(db, returned.id, CreateAfterSalesOrder(resolution_type=resolution, replacement_material_id=line.material_id if resolution == CustomerReturnResolution.REPLACEMENT else None, replacement_lot_id=lot.id if resolution == CustomerReturnResolution.REPLACEMENT else None, execution_notes='维修任务验证' if resolution == CustomerReturnResolution.REPAIR else '执行验证'))
                    order = await quality_service.approve_after_sales_order(db, order.id)
                    order = await quality_service.start_after_sales_order(db, order.id)
                    if resolution == CustomerReturnResolution.REPAIR:
                        task = await quality_service.get_after_sales_repair_task(db, order.id)
                        await quality_service.complete_after_sales_repair_task(db, order.id, CompleteAfterSalesRepairTask(result_notes='维修完成并通过功能复核'))
                        if not task.task_no:
                            raise RuntimeError('repair task missing')
                    order = await quality_service.complete_after_sales_order(db, order.id)
                    if order.status != AfterSalesExecutionStatus.COMPLETED:
                        raise RuntimeError(f'{resolution} did not complete')
                    await quality_service.close_customer_return(db, returned.id)
                    audits = await db.scalars(select(CustomerAfterSalesAudit).where(CustomerAfterSalesAudit.after_sales_order_id == order.id, CustomerAfterSalesAudit.deleted == 0))
                    if len(audits.all()) < 4:
                        raise RuntimeError(f'{resolution} audit trail incomplete')

                print('CUSTOMER_AFTER_SALES_RUN_OK types=REFUND,REPLACEMENT,REPAIR,SCRAP')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('CUSTOMER_AFTER_SALES_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain test data instead of rolling back')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
