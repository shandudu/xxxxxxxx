"""Exercise customer complaint -> RMA -> NCR -> CAPA closure and roll back by default."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.customer.model import Customer
from backend.plugin.demo.service.demo_service import SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.quality.enums import CapaActionStatus, CapaActionType, CapaVerificationResult, DispositionType, InspectionResult
from backend.plugin.quality.model import CustomerReturnLine, NonconformanceReport, QualityCapa, QualityInspection
from backend.plugin.quality.schema.quality import CompleteAfterSalesRepairTask, CompleteCustomerReturnInspection, CompleteInspection, CreateAfterSalesOrder, CreateCapa, CreateCapaAction, CreateCustomerComplaint, CreateCustomerReturn, CreateDisposition, SetCapaActionStatus, VerifyCapa, ResolveCustomerReturn
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
                    raise RuntimeError('demo customer/shipment/lot/warehouse data missing')

                complaint = await quality_service.create_customer_complaint(db, CreateCustomerComplaint(customer_id=customer.id, shipment_id=shipment.id, material_id=line.material_id, lot_id=lot.id, quantity=Decimal('2'), title='客户退货质量投诉', description='RMA rollback validation'))
                rma = await quality_service.create_customer_return(db, CreateCustomerReturn(complaint_id=complaint.id, shipment_id=shipment.id, lines=[{'shipment_line_id': line.id, 'material_id': line.material_id, 'lot_id': lot.id, 'warehouse_id': warehouse.id, 'location_id': location.id, 'quantity': Decimal('2')}]))
                rma = await quality_service.receive_customer_return(db, rma.id)
                rma = await quality_service.inspect_customer_return(db, rma.id, CompleteCustomerReturnInspection(line_id=rma.lines[0].id, accepted_quantity=Decimal('0'), rejected_quantity=Decimal('2'), result=InspectionResult.FAIL, conclusion='退货检验不合格'))
                if not rma.ncr_id:
                    raise RuntimeError('RMA inspection did not create NCR')

                ncr = await quality_service.get_ncr(db, rma.ncr_id)
                disposition = await quality_service.create_disposition(db, CreateDisposition(disposition_no='RMA-ROLLBACK-MRB-001', ncr_id=ncr.id, disposition_type=DispositionType.REINSPECT, quantity=Decimal('2'), decision_reason='RMA rollback'))
                await quality_service.execute_disposition(db, disposition.id)
                retest = await db.scalar(select(QualityInspection).where(QualityInspection.id == disposition.reinspection_id, QualityInspection.deleted == 0))
                await quality_service.complete_inspection(db, retest.id, CompleteInspection(accepted_quantity=Decimal('2'), rejected_quantity=Decimal('0'), result=InspectionResult.PASS, conclusion='复检通过'))
                capa = await quality_service.create_capa(db, CreateCapa(capa_no='RMA-ROLLBACK-CAPA-001', ncr_id=ncr.id, d2_problem_description='客户退货不合格', d4_root_cause='运输或过程异常', d5_corrective_plan='纠正并预防再发'))
                action = await quality_service.create_capa_action(db, capa.id, CreateCapaAction(action_type=CapaActionType.CORRECTIVE, description='完成纠正措施'))
                await quality_service.set_capa_action_status(db, capa.id, action.id, SetCapaActionStatus(status=CapaActionStatus.COMPLETED, evidence='已完成'))
                await quality_service.verify_capa(db, capa.id, VerifyCapa(result=CapaVerificationResult.PASS, notes='验证通过'))
                await quality_service.close_capa(db, capa.id)
                await quality_service.close_ncr(db, ncr.id, 'RMA CAPA 根因已关闭')
                await quality_service.resolve_customer_return(db, rma.id, ResolveCustomerReturn(resolution_type='REFUND', resolution_notes='退款完成'))
                after_sales = await quality_service.create_after_sales_order(db, rma.id, CreateAfterSalesOrder(resolution_type='REFUND', execution_notes='退款执行验证'))
                await quality_service.approve_after_sales_order(db, after_sales.id)
                await quality_service.start_after_sales_order(db, after_sales.id)
                await quality_service.complete_after_sales_order(db, after_sales.id)
                await quality_service.close_customer_return(db, rma.id)
                final = await db.scalar(select(NonconformanceReport).where(NonconformanceReport.id == ncr.id))
                final_rma = await quality_service.list_customer_returns(db)
                if not final or getattr(final.status, 'value', final.status) != 'CLOSED' or not any(item.id == rma.id and getattr(item.status, 'value', item.status) == 'CLOSED' for item in final_rma):
                    raise RuntimeError('RMA/NCR closure failed')
                print('CUSTOMER_RMA_RUN_OK status=CLOSED')
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('CUSTOMER_RMA_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true', help='retain test data instead of rolling back')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
