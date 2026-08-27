from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.bom.model import Bom, BomItem
from backend.plugin.bom.schema.bom import CreateBomItemParam, CreateBomParam
from backend.plugin.bom.service.bom_service import bom_service
from backend.plugin.customer.enums import CompanyType as CustomerCompanyType, CustomerType
from backend.plugin.customer.model import Customer, CustomerCategory
from backend.plugin.customer.schema.customer import CreateCustomerCategoryParam, CreateCustomerParam
from backend.plugin.customer.service.customer_service import customer_service
from backend.plugin.demo.enums import DemoRunStatus
from backend.plugin.demo.model import ManufacturingDemoRun
from backend.plugin.demo.schema.demo import ManufacturingDemoRunDetail, ManufacturingDemoStatus, ManufacturingDemoVerifyResult
from backend.plugin.planning.enums import MpsPlanStatus, MrpRunStatus, PlannedOrderStatus, PlannedOrderType
from backend.plugin.planning.model import MpsDemand, MpsPlan, MrpRun, PlannedOrder
from backend.plugin.planning.schema.planning import CreateMrpRun, CreateMpsPlan, ImportSalesOrderDemand, ReleasePlannedOrder
from backend.plugin.planning.service.planning_service import planning_service
from backend.plugin.material.enums import MaterialType
from backend.plugin.material.model import Material, MaterialCategory, UnitOfMeasure
from backend.plugin.material.schema.material import CreateCategoryParam, CreateMaterialParam, CreateUnitParam
from backend.plugin.material.service.material_service import material_service
from backend.plugin.production.model import MaterialIssue, ProductionExecution, ProductionReport, WorkOrder
from backend.plugin.production.schema.execution import CompleteProductionExecution, RecordMaterialConsumption, StartProductionExecution
from backend.plugin.production.schema.production import CreateMaterialIssue, CreateProductionReport, CreateWorkOrder, MaterialIssueLineConfig
from backend.plugin.production.service.execution_service import production_execution_service
from backend.plugin.production.service.production_service import production_service
from backend.plugin.purchasing.model import PurchaseOrder, SupplierReceipt
from backend.plugin.purchasing.schema.purchasing import CreatePurchaseOrder, CreatePurchaseOrderLine, CreateSupplierReceipt, CreateSupplierReceiptLine
from backend.plugin.purchasing.service.purchasing_service import purchasing_service
from backend.plugin.quality.enums import InspectionResult, InspectionStatus, InspectionType
from backend.plugin.quality.model import QualityInspection
from backend.plugin.quality.schema.quality import CompleteInspection, CreateInspection
from backend.plugin.quality.service.quality_service import quality_service
from backend.plugin.routing.enums import OperationType, WorkCenterType
from backend.plugin.routing.model import Operation, Routing, RoutingOperation, WorkCenter
from backend.plugin.routing.schema.routing import ActivateRoutingParam, CreateOperationParam, CreateRoutingOperationParam, CreateRoutingParam, CreateWorkCenterParam
from backend.plugin.routing.service.routing_service import routing_service
from backend.plugin.sales.model import SalesOrder, SalesOrderLine, Shipment
from backend.plugin.sales.schema.sales import CreateSalesOrder, CreateSalesOrderLine, CreateShipment, CreateShipmentLine
from backend.plugin.sales.service.sales_service import sales_service
from backend.plugin.supplier.enums import CompanyType as SupplierCompanyType, SupplierType
from backend.plugin.supplier.model import Supplier, SupplierCategory
from backend.plugin.supplier.schema.supplier import CreateSupplierCategoryParam, CreateSupplierParam
from backend.plugin.supplier.service.supplier_service import supplier_service
from backend.plugin.trace.enums import QualityStatus, TraceObjectType, TraceRelationType
from backend.plugin.trace.model import MaterialLot, TraceRelation
from backend.plugin.trace.schema.trace import CreateTraceRelationParam
from backend.plugin.trace.service.trace_service import trace_service
from backend.plugin.warehouse.enums import AreaType, LocationType, WarehouseType
from backend.plugin.warehouse.model import Area, Location, Warehouse
from backend.plugin.warehouse.schema.warehouse import CreateAreaConfig, CreateLocationConfig, CreateWarehouseConfig
from backend.plugin.warehouse.service.warehouse_service import warehouse_service
from backend.utils.timezone import timezone


SCENARIO = 'MANUFACTURING_HAPPY_PATH'
SALES_ORDER_DRIVEN_SCENARIO = 'SALES_ORDER_DRIVEN_HAPPY_PATH'
REMARK = 'MES_DEMO:MANUFACTURING_HAPPY_PATH'
SALES_ORDER_DRIVEN_REMARK = 'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH'
QTY = Decimal('10')
REFERENCES = {
    'supplier': 'DEMO-SUP-001', 'customer': 'DEMO-CUS-001', 'unit': 'DEMO-EA',
    'category': 'DEMO-MFG', 'warehouse': 'DEMO-WH-001', 'location': 'DEMO-LOC-001',
    'raw_material': 'DEMO-RM-001', 'finished_material': 'DEMO-FG-001',
    'operation': 'DEMO-OP-001', 'work_center': 'DEMO-WC-001', 'bom': 'DEMO-BOM-FG-001',
    'routing': 'DEMO-RT-FG-001', 'purchase_order': 'DEMO-PO-001', 'receipt': 'DEMO-RCV-001',
    'raw_lot': 'DEMO-RM-LOT-001', 'work_order': 'DEMO-WO-001', 'issue': 'DEMO-ISS-001',
    'execution': 'DEMO-EXE-001', 'report': 'DEMO-RPT-001', 'finished_lot': 'DEMO-FG-LOT-001',
    'inspection': 'DEMO-QI-001', 'sales_order': 'DEMO-SO-001', 'shipment': 'DEMO-SHP-001',
}
SALES_ORDER_DRIVEN_REFERENCES = {
    'raw_material': 'DEMO-SOD-RM-001', 'finished_material': 'DEMO-SOD-FG-001',
    'bom': 'DEMO-SOD-BOM-FG-001', 'routing': 'DEMO-SOD-RT-FG-001',
    'sales_order': 'DEMO-SOD-SO-001', 'mps_plan': 'DEMO-SOD-MPS-001',
    'receipt': 'DEMO-SOD-RCV-001', 'raw_lot': 'DEMO-SOD-RM-LOT-001',
    'issue': 'DEMO-SOD-ISS-001', 'execution': 'DEMO-SOD-EXE-001',
    'report': 'DEMO-SOD-RPT-001', 'finished_lot': 'DEMO-SOD-FG-LOT-001',
    'inspection': 'DEMO-SOD-QI-001', 'shipment': 'DEMO-SOD-SHP-001',
}


class DemoService:
    @staticmethod
    async def _one(db: AsyncSession, model, field, code: str):
        return await db.scalar(select(model).where(field == code, model.deleted == 0))

    @staticmethod
    async def _ensure_master_data(db: AsyncSession) -> dict[str, object]:
        unit = await DemoService._one(db, UnitOfMeasure, UnitOfMeasure.unit_code, REFERENCES['unit'])
        if not unit:
            unit = await material_service.create_unit(db, CreateUnitParam(unit_code=REFERENCES['unit'], unit_name='演示件', symbol='EA', decimal_places=0, remark=REMARK))
        category = await DemoService._one(db, MaterialCategory, MaterialCategory.category_code, REFERENCES['category'])
        if not category:
            category = await material_service.create_category(db, CreateCategoryParam(category_code=REFERENCES['category'], category_name='演示制造物料', remark=REMARK))
        warehouse = await DemoService._one(db, Warehouse, Warehouse.warehouse_code, REFERENCES['warehouse'])
        if not warehouse:
            warehouse = await warehouse_service.create_warehouse(db, CreateWarehouseConfig(warehouse_code=REFERENCES['warehouse'], warehouse_name='演示制造仓', warehouse_type=WarehouseType.RAW_MATERIAL, remark=REMARK))
        area = await DemoService._one(db, Area, Area.area_code, 'DEMO-AREA-001')
        if not area:
            area = await warehouse_service.create_area(db, CreateAreaConfig(area_code='DEMO-AREA-001', area_name='演示收发区', warehouse_id=warehouse.id, area_type=AreaType.NORMAL, remark=REMARK))
        location = await DemoService._one(db, Location, Location.location_code, REFERENCES['location'])
        if not location:
            location = await warehouse_service.create_location(db, CreateLocationConfig(warehouse_id=warehouse.id, area_id=area.id, location_code=REFERENCES['location'], location_name='演示库位', location_type=LocationType.BIN, storage_enabled=True, mixed_material_allowed=True, mixed_lot_allowed=True, remark=REMARK))
        raw = await DemoService._one(db, Material, Material.material_code, REFERENCES['raw_material'])
        if not raw:
            raw = await material_service.create_material(db, CreateMaterialParam(material_code=REFERENCES['raw_material'], material_name='演示原材料', material_type=MaterialType.RAW_MATERIAL, category_id=category.id, base_unit_id=unit.id, batch_control=True, purchasable=True, default_warehouse_id=warehouse.id, remark=REMARK))
        finished = await DemoService._one(db, Material, Material.material_code, REFERENCES['finished_material'])
        if not finished:
            finished = await material_service.create_material(db, CreateMaterialParam(material_code=REFERENCES['finished_material'], material_name='演示成品', material_type=MaterialType.FINISHED_PRODUCT, category_id=category.id, base_unit_id=unit.id, batch_control=True, producible=True, sellable=True, quality_inspection_required=True, default_warehouse_id=warehouse.id, remark=REMARK))
        supplier_category = await DemoService._one(db, SupplierCategory, SupplierCategory.category_code, 'DEMO-SUP-CAT')
        if not supplier_category:
            supplier_category = await supplier_service.create_category(db, CreateSupplierCategoryParam(category_code='DEMO-SUP-CAT', category_name='演示供应商分类', remark=REMARK))
        supplier = await DemoService._one(db, Supplier, Supplier.supplier_code, REFERENCES['supplier'])
        if not supplier:
            supplier_category_id = supplier_category.id if isinstance(supplier_category, SupplierCategory) else supplier_category['id']
            supplier_data = CreateSupplierParam(supplier_code=REFERENCES['supplier'], supplier_name='演示原料供应商', category_id=supplier_category_id, supplier_type=SupplierType.MATERIAL, company_type=SupplierCompanyType.COMPANY, remark=REMARK)
            await supplier_service.create_supplier(db, supplier_data)
            supplier = await DemoService._one(db, Supplier, Supplier.supplier_code, REFERENCES['supplier'])
        customer_category = await DemoService._one(db, CustomerCategory, CustomerCategory.category_code, 'DEMO-CUS-CAT')
        if not customer_category:
            customer_category = await customer_service.create_category(db, CreateCustomerCategoryParam(category_code='DEMO-CUS-CAT', category_name='演示客户分类', remark=REMARK))
        customer = await DemoService._one(db, Customer, Customer.customer_code, REFERENCES['customer'])
        if not customer:
            customer = await customer_service.create_customer(db, CreateCustomerParam(customer_code=REFERENCES['customer'], customer_name='演示成品客户', category_id=customer_category.id, customer_type=CustomerType.ENTERPRISE, company_type=CustomerCompanyType.COMPANY, remark=REMARK))
        operation = await DemoService._one(db, Operation, Operation.operation_code, REFERENCES['operation'])
        if not operation:
            operation = await routing_service.create_operation(db, CreateOperationParam(operation_code=REFERENCES['operation'], operation_name='演示装配', operation_type=OperationType.ASSEMBLY, trace_enabled=True, quality_enabled=True, remark=REMARK))
        center = await DemoService._one(db, WorkCenter, WorkCenter.work_center_code, REFERENCES['work_center'])
        if not center:
            center = await routing_service.create_work_center(db, CreateWorkCenterParam(work_center_code=REFERENCES['work_center'], work_center_name='演示装配单元', work_center_type=WorkCenterType.CELL, capacity_value=Decimal('60'), capacity_unit='EA/H', remark=REMARK))
        return {'unit': unit, 'category': category, 'warehouse': warehouse, 'location': location, 'raw': raw, 'finished': finished, 'supplier': supplier, 'customer': customer, 'operation': operation, 'center': center}

    @staticmethod
    async def _ensure_definition(db: AsyncSession, data: dict[str, object]) -> tuple[Bom, Routing]:
        bom = await DemoService._one(db, Bom, Bom.bom_code, REFERENCES['bom'])
        if not bom:
            bom = await bom_service.create_bom(db, CreateBomParam(bom_code=REFERENCES['bom'], product_material_id=data['finished'].id, bom_version='V1', remark=REMARK))
            await bom_service.add_item(db, bom.id, CreateBomItemParam(line_no=10, component_material_id=data['raw'].id, quantity=Decimal('1'), unit_id=data['unit'].id, remark=REMARK))
            await bom_service.activate_bom(db, bom.id)
        routing = await DemoService._one(db, Routing, Routing.routing_code, REFERENCES['routing'])
        if not routing:
            routing = await routing_service.create_routing(db, CreateRoutingParam(routing_code=REFERENCES['routing'], routing_name='演示成品标准工艺', product_material_id=data['finished'].id, routing_version='V1', remark=REMARK))
            await routing_service.add_routing_operation(db, routing.id, CreateRoutingOperationParam(sequence_no=10, operation_id=data['operation'].id, work_center_id=data['center'].id, run_time_value=Decimal('1'), remark=REMARK))
            await routing_service.activate_routing(db, routing.id, ActivateRoutingParam(set_as_default=True))
        return bom, routing

    @staticmethod
    async def _ensure_sales_order_materials(db: AsyncSession, data: dict[str, object]) -> dict[str, object]:
        """Create isolated scenario materials while reusing shared demo master data."""
        raw = await DemoService._one(db, Material, Material.material_code, SALES_ORDER_DRIVEN_REFERENCES['raw_material'])
        if not raw:
            raw = await material_service.create_material(
                db,
                CreateMaterialParam(
                    material_code=SALES_ORDER_DRIVEN_REFERENCES['raw_material'],
                    material_name='销售驱动演示原材料',
                    material_type=MaterialType.RAW_MATERIAL,
                    category_id=data['category'].id,
                    base_unit_id=data['unit'].id,
                    batch_control=True,
                    purchasable=True,
                    default_warehouse_id=data['warehouse'].id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
        finished = await DemoService._one(
            db, Material, Material.material_code, SALES_ORDER_DRIVEN_REFERENCES['finished_material']
        )
        if not finished:
            finished = await material_service.create_material(
                db,
                CreateMaterialParam(
                    material_code=SALES_ORDER_DRIVEN_REFERENCES['finished_material'],
                    material_name='销售驱动演示成品',
                    material_type=MaterialType.FINISHED_PRODUCT,
                    category_id=data['category'].id,
                    base_unit_id=data['unit'].id,
                    batch_control=True,
                    producible=True,
                    sellable=True,
                    quality_inspection_required=True,
                    default_warehouse_id=data['warehouse'].id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
        return {**data, 'raw': raw, 'finished': finished}

    @staticmethod
    async def _ensure_sales_order_definition(db: AsyncSession, data: dict[str, object]) -> tuple[Bom, Routing]:
        bom = await DemoService._one(db, Bom, Bom.bom_code, SALES_ORDER_DRIVEN_REFERENCES['bom'])
        if not bom:
            bom = await bom_service.create_bom(
                db,
                CreateBomParam(
                    bom_code=SALES_ORDER_DRIVEN_REFERENCES['bom'],
                    product_material_id=data['finished'].id,
                    bom_version='V1',
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await bom_service.add_item(
                db,
                bom.id,
                CreateBomItemParam(
                    line_no=10,
                    component_material_id=data['raw'].id,
                    quantity=Decimal('1'),
                    unit_id=data['unit'].id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await bom_service.activate_bom(db, bom.id)
        routing = await DemoService._one(
            db, Routing, Routing.routing_code, SALES_ORDER_DRIVEN_REFERENCES['routing']
        )
        if not routing:
            routing = await routing_service.create_routing(
                db,
                CreateRoutingParam(
                    routing_code=SALES_ORDER_DRIVEN_REFERENCES['routing'],
                    routing_name='销售驱动演示成品工艺',
                    product_material_id=data['finished'].id,
                    routing_version='V1',
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await routing_service.add_routing_operation(
                db,
                routing.id,
                CreateRoutingOperationParam(
                    sequence_no=10,
                    operation_id=data['operation'].id,
                    work_center_id=data['center'].id,
                    run_time_value=Decimal('1'),
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await routing_service.activate_routing(db, routing.id, ActivateRoutingParam(set_as_default=True))
        return bom, routing

    @staticmethod
    async def run(db: AsyncSession) -> ManufacturingDemoRunDetail:
        existing = await db.scalar(select(ManufacturingDemoRun).where(ManufacturingDemoRun.scenario_code == SCENARIO, ManufacturingDemoRun.deleted == 0).with_for_update())
        if existing and existing.status == DemoRunStatus.COMPLETED:
            return ManufacturingDemoRunDetail.model_validate(existing)
        now = timezone.now()
        run = existing or ManufacturingDemoRun(run_no=f'DEMO-{uuid4().hex[:12].upper()}', scenario_code=SCENARIO, status=DemoRunStatus.RUNNING, started_at=now)
        if not existing:
            db.add(run)
        data = await DemoService._ensure_master_data(db)
        bom, routing = await DemoService._ensure_definition(db, data)
        po = await DemoService._one(db, PurchaseOrder, PurchaseOrder.purchase_order_no, REFERENCES['purchase_order'])
        if not po:
            po_detail = await purchasing_service.create_order(db, CreatePurchaseOrder(purchase_order_no=REFERENCES['purchase_order'], supplier_id=data['supplier'].id, remark=REMARK, lines=[CreatePurchaseOrderLine(material_id=data['raw'].id, ordered_quantity=QTY, unit_price=Decimal('1'))]))
            await purchasing_service.confirm_order(db, po_detail.id)
            po = await DemoService._one(db, PurchaseOrder, PurchaseOrder.purchase_order_no, REFERENCES['purchase_order'])
        receipt = await DemoService._one(db, SupplierReceipt, SupplierReceipt.receipt_no, REFERENCES['receipt'])
        if not receipt:
            line = (await purchasing_service.get_order(db, po.id)).lines[0]
            await purchasing_service.create_receipt(db, CreateSupplierReceipt(receipt_no=REFERENCES['receipt'], purchase_order_id=po.id, remark=REMARK, lines=[CreateSupplierReceiptLine(purchase_order_line_id=line.id, warehouse_id=data['warehouse'].id, location_id=data['location'].id, quantity=QTY, lot_no=REFERENCES['raw_lot'], supplier_lot_no='SUP-LOT-001')]))
        raw_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, REFERENCES['raw_lot'])
        order = await DemoService._one(db, WorkOrder, WorkOrder.work_order_no, REFERENCES['work_order'])
        if not order:
            order_detail = await production_service.create_order(db, CreateWorkOrder(work_order_no=REFERENCES['work_order'], product_material_id=data['finished'].id, bom_id=bom.id, routing_id=routing.id, planned_quantity=QTY, remark=REMARK))
            await production_service.release_order(db, order_detail.id)
            order = await DemoService._one(db, WorkOrder, WorkOrder.work_order_no, REFERENCES['work_order'])
        issue = await DemoService._one(db, MaterialIssue, MaterialIssue.issue_no, REFERENCES['issue'])
        if not issue:
            detail = await production_service.get_order(db, order.id)
            issued = await production_service.issue_material(db, CreateMaterialIssue(issue_no=REFERENCES['issue'], work_order_id=order.id, remark=REMARK, lines=[MaterialIssueLineConfig(requirement_id=detail.requirements[0].id, lot_id=raw_lot.id, warehouse_id=data['warehouse'].id, location_id=data['location'].id, quantity=QTY)]))
            issue_line_id = issued.lines[0].id
        else:
            issue_line_id = (await production_service.list_issues(db, order.id))[0].lines[0].id
        execution = await db.scalar(select(ProductionExecution).where(ProductionExecution.execution_no == REFERENCES['execution'], ProductionExecution.deleted == 0))
        if not execution:
            detail = await production_service.get_order(db, order.id)
            execution_detail = await production_execution_service.start(db, order.id, detail.operations[0].id, StartProductionExecution(execution_no=REFERENCES['execution'], remark=REMARK))
            await production_execution_service.consume(db, execution_detail.id, RecordMaterialConsumption(consumption_no='DEMO-CON-001', requirement_id=detail.requirements[0].id, issue_line_id=issue_line_id, quantity=QTY, remark=REMARK))
            await production_execution_service.complete(db, execution_detail.id, CompleteProductionExecution(good_quantity=QTY, remark=REMARK))
        finished_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, REFERENCES['finished_lot'])
        if not finished_lot:
            await production_service.report_completion(db, CreateProductionReport(report_no=REFERENCES['report'], work_order_id=order.id, good_quantity=QTY, warehouse_id=data['warehouse'].id, location_id=data['location'].id, lot_no=REFERENCES['finished_lot'], remark=REMARK))
            finished_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, REFERENCES['finished_lot'])
        relation = await db.scalar(select(TraceRelation.id).where(TraceRelation.source_id == raw_lot.id, TraceRelation.target_id == finished_lot.id, TraceRelation.deleted == 0))
        if not relation:
            await trace_service.create_relation(db, CreateTraceRelationParam(source_type=TraceObjectType.LOT, source_id=raw_lot.id, target_type=TraceObjectType.LOT, target_id=finished_lot.id, relation_type=TraceRelationType.CONSUMED_TO, quantity=QTY, unit_id=data['unit'].id, business_ref_type='WORK_ORDER', business_ref_id=order.id, business_ref_no=order.work_order_no, remark=REMARK))
        inspection = await DemoService._one(db, QualityInspection, QualityInspection.inspection_no, REFERENCES['inspection'])
        if not inspection:
            inspection = await quality_service.create_inspection(db, CreateInspection(inspection_no=REFERENCES['inspection'], inspection_type=InspectionType.FINAL, material_id=data['finished'].id, lot_id=finished_lot.id, source_type='PRODUCTION_REPORT', source_id=order.id, source_no=REFERENCES['report'], sample_quantity=QTY))
            await quality_service.complete_inspection(db, inspection.id, CompleteInspection(accepted_quantity=QTY, rejected_quantity=Decimal('0'), result=InspectionResult.PASS, conclusion='演示成品检验合格'))
        so = await DemoService._one(db, SalesOrder, SalesOrder.sales_order_no, REFERENCES['sales_order'])
        if not so:
            so_detail = await sales_service.create_order(db, CreateSalesOrder(sales_order_no=REFERENCES['sales_order'], customer_id=data['customer'].id, remark=REMARK, lines=[CreateSalesOrderLine(material_id=data['finished'].id, ordered_quantity=QTY, unit_price=Decimal('10'))]))
            await sales_service.transition(db, so_detail.id, 'confirm')
            so = await DemoService._one(db, SalesOrder, SalesOrder.sales_order_no, REFERENCES['sales_order'])
        shipment = await DemoService._one(db, Shipment, Shipment.shipment_no, REFERENCES['shipment'])
        if not shipment:
            line = (await sales_service.get_order(db, so.id)).lines[0]
            await sales_service.create_shipment(db, CreateShipment(shipment_no=REFERENCES['shipment'], sales_order_id=so.id, remark=REMARK, lines=[CreateShipmentLine(sales_order_line_id=line.id, lot_id=finished_lot.id, warehouse_id=data['warehouse'].id, location_id=data['location'].id, quantity=QTY)]))
        run.status, run.completed_at, run.failed_step, run.error_message = DemoRunStatus.COMPLETED, timezone.now(), None, None
        await db.flush()
        return ManufacturingDemoRunDetail.model_validate(run)

    @staticmethod
    async def verify_sales_order_driven(db: AsyncSession) -> ManufacturingDemoVerifyResult:
        completed: list[str] = []
        missing: list[str] = []
        references = dict(SALES_ORDER_DRIVEN_REFERENCES)
        so = await DemoService._one(
            db, SalesOrder, SalesOrder.sales_order_no, SALES_ORDER_DRIVEN_REFERENCES['sales_order']
        )
        if so and getattr(so.status, 'value', so.status) in {'CONFIRMED', 'PARTIALLY_SHIPPED', 'SHIPPED'}:
            completed.append('sales_order_confirmed')
        else:
            missing.append('sales_order_confirmed')
        line = await db.scalar(
            select(SalesOrderLine).where(
                SalesOrderLine.sales_order_id == so.id if so else False,
                SalesOrderLine.deleted == 0,
            ).order_by(SalesOrderLine.line_no)
        ) if so else None
        plan = await DemoService._one(db, MpsPlan, MpsPlan.plan_no, SALES_ORDER_DRIVEN_REFERENCES['mps_plan'])
        demand = await db.scalar(
            select(MpsDemand).where(
                MpsDemand.mps_plan_id == plan.id if plan else False,
                MpsDemand.source_id == line.id if line else False,
                MpsDemand.deleted == 0,
            )
        ) if plan and line else None
        if plan and plan.status == MpsPlanStatus.CONFIRMED and demand:
            completed.append('mps_demand')
        else:
            missing.append('mps_demand')
        mrp = await db.scalar(
            select(MrpRun).where(
                MrpRun.mps_plan_id == plan.id if plan else False,
                MrpRun.status == MrpRunStatus.COMPLETED,
                MrpRun.deleted == 0,
            ).order_by(MrpRun.id.desc())
        ) if plan else None
        planned_orders = (
            await db.scalars(
                select(PlannedOrder).where(
                    PlannedOrder.mrp_run_id == mrp.id if mrp else False,
                    PlannedOrder.deleted == 0,
                )
            )
        ).all() if mrp else []
        purchase_plan = next((item for item in planned_orders if item.order_type == PlannedOrderType.PURCHASE), None)
        production_plan = next((item for item in planned_orders if item.order_type == PlannedOrderType.PRODUCTION), None)
        if mrp and purchase_plan and production_plan:
            completed.append('mrp_supply_plan')
        else:
            missing.append('mrp_supply_plan')
        po = await db.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.id == purchase_plan.source_document_id if purchase_plan and purchase_plan.source_document_id else False,
                PurchaseOrder.deleted == 0,
            )
        ) if purchase_plan and purchase_plan.source_document_id else None
        receipt = await DemoService._one(db, SupplierReceipt, SupplierReceipt.receipt_no, SALES_ORDER_DRIVEN_REFERENCES['receipt'])
        raw_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, SALES_ORDER_DRIVEN_REFERENCES['raw_lot'])
        if po and purchase_plan.status == PlannedOrderStatus.RELEASED and receipt and raw_lot:
            completed.append('purchase_receipt')
        else:
            missing.append('purchase_receipt')
        order = await db.scalar(
            select(WorkOrder).where(
                WorkOrder.id == production_plan.source_document_id if production_plan and production_plan.source_document_id else False,
                WorkOrder.deleted == 0,
            )
        ) if production_plan and production_plan.source_document_id else None
        report = await DemoService._one(db, ProductionReport, ProductionReport.report_no, SALES_ORDER_DRIVEN_REFERENCES['report'])
        finished_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, SALES_ORDER_DRIVEN_REFERENCES['finished_lot'])
        if order and order.status == 'COMPLETED' and report and finished_lot:
            completed.append('production_report')
        else:
            missing.append('production_report')
        inspection = await db.scalar(
            select(QualityInspection).where(
                QualityInspection.lot_id == finished_lot.id if finished_lot else False,
                QualityInspection.inspection_type == InspectionType.FINAL,
                QualityInspection.deleted == 0,
            ).order_by(QualityInspection.id.desc())
        ) if finished_lot else None
        if inspection and inspection.status == InspectionStatus.COMPLETED and inspection.result == InspectionResult.PASS:
            completed.append('final_quality_pass')
        else:
            missing.append('final_quality_pass')
        shipment = await DemoService._one(db, Shipment, Shipment.shipment_no, SALES_ORDER_DRIVEN_REFERENCES['shipment'])
        if shipment and so and so.status == 'SHIPPED':
            completed.append('shipment')
        else:
            missing.append('shipment')
        if raw_lot and finished_lot and await db.scalar(
            select(TraceRelation.id).where(
                TraceRelation.source_id == raw_lot.id,
                TraceRelation.target_id == finished_lot.id,
                TraceRelation.deleted == 0,
            )
        ):
            completed.append('forward_trace')
            completed.append('reverse_trace')
        else:
            missing.extend(['forward_trace', 'reverse_trace'])
        for key, value in {
            'purchase_order': po.purchase_order_no if po else '',
            'work_order': order.work_order_no if order else '',
            'mrp_run': mrp.run_no if mrp else '',
        }.items():
            references[key] = value
        return ManufacturingDemoVerifyResult(
            passed=not missing,
            completed_steps=completed,
            missing_steps=missing,
            references=references,
        )

    @staticmethod
    async def _complete_pass_inspection(
        db: AsyncSession, inspection: QualityInspection | None, conclusion: str
    ) -> QualityInspection | None:
        if inspection and inspection.status == InspectionStatus.PENDING:
            await quality_service.complete_inspection(
                db,
                inspection.id,
                CompleteInspection(
                    accepted_quantity=inspection.sample_quantity,
                    rejected_quantity=Decimal('0'),
                    result=InspectionResult.PASS,
                    conclusion=conclusion,
                ),
            )
        return inspection

    @staticmethod
    async def run_sales_order_driven(db: AsyncSession) -> ManufacturingDemoRunDetail:
        """Run the demand-driven scenario through planning instead of creating supply directly."""
        existing = await db.scalar(
            select(ManufacturingDemoRun)
            .where(
                ManufacturingDemoRun.scenario_code == SALES_ORDER_DRIVEN_SCENARIO,
                ManufacturingDemoRun.deleted == 0,
            )
            .with_for_update()
        )
        if existing and existing.status == DemoRunStatus.COMPLETED:
            return ManufacturingDemoRunDetail.model_validate(existing)
        run = existing or ManufacturingDemoRun(
            run_no=f'DEMO-SOD-{uuid4().hex[:12].upper()}',
            scenario_code=SALES_ORDER_DRIVEN_SCENARIO,
            status=DemoRunStatus.RUNNING,
            started_at=timezone.now(),
        )
        if not existing:
            db.add(run)
            await db.flush()

        data = await DemoService._ensure_sales_order_materials(db, await DemoService._ensure_master_data(db))
        bom, routing = await DemoService._ensure_sales_order_definition(db, data)
        so = await DemoService._one(
            db, SalesOrder, SalesOrder.sales_order_no, SALES_ORDER_DRIVEN_REFERENCES['sales_order']
        )
        if not so:
            so_detail = await sales_service.create_order(
                db,
                CreateSalesOrder(
                    sales_order_no=SALES_ORDER_DRIVEN_REFERENCES['sales_order'],
                    customer_id=data['customer'].id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                    lines=[
                        CreateSalesOrderLine(
                            material_id=data['finished'].id,
                            ordered_quantity=QTY,
                            unit_price=Decimal('10'),
                        )
                    ],
                ),
            )
            await sales_service.transition(db, so_detail.id, 'confirm')
            so = await DemoService._one(
                db, SalesOrder, SalesOrder.sales_order_no, SALES_ORDER_DRIVEN_REFERENCES['sales_order']
            )
        elif getattr(so.status, 'value', so.status) == 'DRAFT':
            await sales_service.transition(db, so.id, 'confirm')
        if not so:
            raise errors.ConflictError(msg='SOD_SALES_ORDER_NOT_CREATED')

        sales_line = await db.scalar(
            select(SalesOrderLine).where(
                SalesOrderLine.sales_order_id == so.id, SalesOrderLine.deleted == 0
            ).order_by(SalesOrderLine.line_no)
        )
        if not sales_line:
            raise errors.ConflictError(msg='SOD_SALES_ORDER_LINE_NOT_FOUND')

        today = timezone.now().date()
        plan = await DemoService._one(
            db, MpsPlan, MpsPlan.plan_no, SALES_ORDER_DRIVEN_REFERENCES['mps_plan']
        )
        if not plan:
            plan = await planning_service.create_plan(
                db,
                CreateMpsPlan(
                    plan_no=SALES_ORDER_DRIVEN_REFERENCES['mps_plan'],
                    plan_name='销售订单驱动演示计划',
                    horizon_start=today,
                    horizon_end=today + timedelta(days=30),
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            plan = await db.scalar(select(MpsPlan).where(MpsPlan.id == plan.id))
        if not plan:
            raise errors.ConflictError(msg='SOD_MPS_PLAN_NOT_CREATED')
        if plan.status == MpsPlanStatus.DRAFT:
            await planning_service.import_sales_orders(
                db,
                plan.id,
                ImportSalesOrderDemand(sales_order_ids=[so.id], demand_date=today + timedelta(days=7)),
            )
            await planning_service.confirm_plan(db, plan.id)
        demand = await db.scalar(
            select(MpsDemand).where(
                MpsDemand.mps_plan_id == plan.id,
                MpsDemand.source_id == sales_line.id,
                MpsDemand.deleted == 0,
            )
        )
        if not demand:
            raise errors.ConflictError(msg='SOD_MPS_DEMAND_NOT_CREATED')

        mrp = await db.scalar(
            select(MrpRun).where(
                MrpRun.mps_plan_id == plan.id,
                MrpRun.status == MrpRunStatus.COMPLETED,
                MrpRun.deleted == 0,
            ).order_by(MrpRun.id.desc())
        )
        if not mrp:
            mrp_detail = await planning_service.run_mrp(
                db,
                CreateMrpRun(
                    mps_plan_id=plan.id,
                    include_inventory=True,
                    include_open_purchase=True,
                    include_open_production=True,
                ),
            )
            if mrp_detail.status != MrpRunStatus.COMPLETED:
                raise errors.ConflictError(msg='SOD_MRP_FAILED')
            mrp = await db.scalar(select(MrpRun).where(MrpRun.id == mrp_detail.id))
        if not mrp:
            raise errors.ConflictError(msg='SOD_MRP_NOT_CREATED')
        planned_orders = (
            await db.scalars(
                select(PlannedOrder)
                .where(PlannedOrder.mrp_run_id == mrp.id, PlannedOrder.deleted == 0)
                .order_by(PlannedOrder.sequence_no)
            )
        ).all()
        purchase_plan = next(
            (item for item in planned_orders if item.order_type == PlannedOrderType.PURCHASE and item.material_id == data['raw'].id),
            None,
        )
        production_plan = next(
            (item for item in planned_orders if item.order_type == PlannedOrderType.PRODUCTION and item.material_id == data['finished'].id),
            None,
        )
        if not purchase_plan or not production_plan:
            raise errors.ConflictError(msg='SOD_MRP_SUPPLY_PLAN_INCOMPLETE')

        if purchase_plan.status != PlannedOrderStatus.RELEASED:
            await planning_service.release_planned_order(
                db,
                purchase_plan.id,
                ReleasePlannedOrder(
                    supplier_id=data['supplier'].id,
                    unit_price=Decimal('1'),
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            purchase_plan = await db.scalar(select(PlannedOrder).where(PlannedOrder.id == purchase_plan.id))
        po = await db.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.id == purchase_plan.source_document_id,
                PurchaseOrder.deleted == 0,
            )
        ) if purchase_plan and purchase_plan.source_document_id else None
        if not po:
            raise errors.ConflictError(msg='SOD_PURCHASE_ORDER_NOT_RELEASED')
        if getattr(po.status, 'value', po.status) == 'DRAFT':
            await purchasing_service.confirm_order(db, po.id)
            po = await db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == po.id))
        receipt = await DemoService._one(
            db, SupplierReceipt, SupplierReceipt.receipt_no, SALES_ORDER_DRIVEN_REFERENCES['receipt']
        )
        if not receipt:
            po_detail = await purchasing_service.get_order(db, po.id)
            await purchasing_service.create_receipt(
                db,
                CreateSupplierReceipt(
                    receipt_no=SALES_ORDER_DRIVEN_REFERENCES['receipt'],
                    purchase_order_id=po.id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                    lines=[
                        CreateSupplierReceiptLine(
                            purchase_order_line_id=po_detail.lines[0].id,
                            warehouse_id=data['warehouse'].id,
                            location_id=data['location'].id,
                            quantity=purchase_plan.quantity,
                            lot_no=SALES_ORDER_DRIVEN_REFERENCES['raw_lot'],
                            supplier_lot_no='SOD-SUP-LOT-001',
                            remark=SALES_ORDER_DRIVEN_REMARK,
                        )
                    ],
                ),
            )
            receipt = await DemoService._one(
                db, SupplierReceipt, SupplierReceipt.receipt_no, SALES_ORDER_DRIVEN_REFERENCES['receipt']
            )
        if not receipt:
            raise errors.ConflictError(msg='SOD_RECEIPT_NOT_CREATED')
        raw_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, SALES_ORDER_DRIVEN_REFERENCES['raw_lot'])
        if not raw_lot:
            raise errors.ConflictError(msg='SOD_RAW_LOT_NOT_CREATED')
        incoming = await db.scalar(
            select(QualityInspection).where(
                QualityInspection.source_type == 'SUPPLIER_RECEIPT',
                QualityInspection.source_id == receipt.id,
                QualityInspection.lot_id == raw_lot.id if raw_lot else False,
                QualityInspection.deleted == 0,
            ).order_by(QualityInspection.id.desc())
        ) if raw_lot else None
        if not incoming and raw_lot.quality_status != QualityStatus.PASS:
            incoming = await quality_service.create_inspection(
                db,
                CreateInspection(
                    inspection_no=f"{SALES_ORDER_DRIVEN_REFERENCES['inspection']}-IQC",
                    inspection_type=InspectionType.INCOMING,
                    material_id=data['raw'].id,
                    lot_id=raw_lot.id,
                    source_type='SUPPLIER_RECEIPT',
                    source_id=receipt.id,
                    source_no=receipt.receipt_no,
                    sample_quantity=raw_lot.quantity,
                ),
            )
        await DemoService._complete_pass_inspection(db, incoming, '销售驱动演示来料检验合格')

        if production_plan.status != PlannedOrderStatus.RELEASED:
            await planning_service.release_planned_order(
                db,
                production_plan.id,
                ReleasePlannedOrder(
                    routing_id=routing.id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            production_plan = await db.scalar(select(PlannedOrder).where(PlannedOrder.id == production_plan.id))
        order = await db.scalar(
            select(WorkOrder).where(
                WorkOrder.id == production_plan.source_document_id,
                WorkOrder.deleted == 0,
            )
        ) if production_plan and production_plan.source_document_id else None
        if not order:
            raise errors.ConflictError(msg='SOD_WORK_ORDER_NOT_RELEASED')
        if getattr(order.status, 'value', order.status) == 'DRAFT':
            await production_service.release_order(db, order.id)
        issue = await DemoService._one(db, MaterialIssue, MaterialIssue.issue_no, SALES_ORDER_DRIVEN_REFERENCES['issue'])
        if not issue:
            detail = await production_service.get_order(db, order.id)
            issued = await production_service.issue_material(
                db,
                CreateMaterialIssue(
                    issue_no=SALES_ORDER_DRIVEN_REFERENCES['issue'],
                    work_order_id=order.id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                    lines=[
                        MaterialIssueLineConfig(
                            requirement_id=detail.requirements[0].id,
                            lot_id=raw_lot.id,
                            warehouse_id=data['warehouse'].id,
                            location_id=data['location'].id,
                            quantity=production_plan.quantity,
                        )
                    ],
                ),
            )
            issue_line_id = issued.lines[0].id
        else:
            issue_line_id = (
                await production_service.list_issues(db, order.id)
            )[0].lines[0].id
        execution = await db.scalar(
            select(ProductionExecution).where(
                ProductionExecution.execution_no == SALES_ORDER_DRIVEN_REFERENCES['execution'],
                ProductionExecution.deleted == 0,
            )
        )
        if not execution:
            detail = await production_service.get_order(db, order.id)
            execution_detail = await production_execution_service.start(
                db,
                order.id,
                detail.operations[0].id,
                StartProductionExecution(
                    execution_no=SALES_ORDER_DRIVEN_REFERENCES['execution'],
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await production_execution_service.consume(
                db,
                execution_detail.id,
                RecordMaterialConsumption(
                    consumption_no='DEMO-SOD-CON-001',
                    requirement_id=detail.requirements[0].id,
                    issue_line_id=issue_line_id,
                    quantity=production_plan.quantity,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            await production_execution_service.complete(
                db,
                execution_detail.id,
                CompleteProductionExecution(
                    good_quantity=production_plan.quantity,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
        report = await DemoService._one(db, ProductionReport, ProductionReport.report_no, SALES_ORDER_DRIVEN_REFERENCES['report'])
        if not report:
            await production_service.report_completion(
                db,
                CreateProductionReport(
                    report_no=SALES_ORDER_DRIVEN_REFERENCES['report'],
                    work_order_id=order.id,
                    good_quantity=production_plan.quantity,
                    warehouse_id=data['warehouse'].id,
                    location_id=data['location'].id,
                    lot_no=SALES_ORDER_DRIVEN_REFERENCES['finished_lot'],
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
            report = await DemoService._one(db, ProductionReport, ProductionReport.report_no, SALES_ORDER_DRIVEN_REFERENCES['report'])
        finished_lot = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, SALES_ORDER_DRIVEN_REFERENCES['finished_lot'])
        if not finished_lot or not report:
            raise errors.ConflictError(msg='SOD_PRODUCTION_REPORT_NOT_CREATED')
        inspection = await db.scalar(
            select(QualityInspection).where(
                QualityInspection.source_type == 'PRODUCTION_REPORT',
                QualityInspection.source_id == report.id,
                QualityInspection.lot_id == finished_lot.id,
                QualityInspection.deleted == 0,
            ).order_by(QualityInspection.id.desc())
        )
        if not inspection:
            inspection = await DemoService._one(
                db, QualityInspection, QualityInspection.inspection_no, SALES_ORDER_DRIVEN_REFERENCES['inspection']
            )
        if not inspection:
            inspection = await quality_service.create_inspection(
                db,
                CreateInspection(
                    inspection_no=SALES_ORDER_DRIVEN_REFERENCES['inspection'],
                    inspection_type=InspectionType.FINAL,
                    material_id=data['finished'].id,
                    lot_id=finished_lot.id,
                    source_type='PRODUCTION_REPORT',
                    source_id=report.id,
                    source_no=report.report_no,
                    sample_quantity=production_plan.quantity,
                ),
            )
        await DemoService._complete_pass_inspection(db, inspection, '销售驱动演示终检合格')
        relation = await db.scalar(
            select(TraceRelation.id).where(
                TraceRelation.source_id == raw_lot.id,
                TraceRelation.target_id == finished_lot.id,
                TraceRelation.deleted == 0,
            )
        )
        if not relation:
            await trace_service.create_relation(
                db,
                CreateTraceRelationParam(
                    source_type=TraceObjectType.LOT,
                    source_id=raw_lot.id,
                    target_type=TraceObjectType.LOT,
                    target_id=finished_lot.id,
                    relation_type=TraceRelationType.CONSUMED_TO,
                    quantity=production_plan.quantity,
                    unit_id=data['unit'].id,
                    business_ref_type='WORK_ORDER',
                    business_ref_id=order.id,
                    business_ref_no=order.work_order_no,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                ),
            )
        shipment = await DemoService._one(
            db, Shipment, Shipment.shipment_no, SALES_ORDER_DRIVEN_REFERENCES['shipment']
        )
        if not shipment:
            await sales_service.create_shipment(
                db,
                CreateShipment(
                    shipment_no=SALES_ORDER_DRIVEN_REFERENCES['shipment'],
                    sales_order_id=so.id,
                    remark=SALES_ORDER_DRIVEN_REMARK,
                    lines=[
                        CreateShipmentLine(
                            sales_order_line_id=sales_line.id,
                            lot_id=finished_lot.id,
                            warehouse_id=data['warehouse'].id,
                            location_id=data['location'].id,
                            quantity=QTY,
                        )
                    ],
                ),
            )
        run.status, run.completed_at, run.failed_step, run.error_message = (
            DemoRunStatus.COMPLETED,
            timezone.now(),
            None,
            None,
        )
        await db.flush()
        return ManufacturingDemoRunDetail.model_validate(run)

    @staticmethod
    async def verify(db: AsyncSession) -> ManufacturingDemoVerifyResult:
        checks = {
            'supplier': (Supplier, Supplier.supplier_code, REFERENCES['supplier']), 'customer': (Customer, Customer.customer_code, REFERENCES['customer']),
            'raw_material': (Material, Material.material_code, REFERENCES['raw_material']), 'finished_material': (Material, Material.material_code, REFERENCES['finished_material']),
            'bom': (Bom, Bom.bom_code, REFERENCES['bom']), 'routing': (Routing, Routing.routing_code, REFERENCES['routing']),
            'purchase_order': (PurchaseOrder, PurchaseOrder.purchase_order_no, REFERENCES['purchase_order']), 'receipt': (SupplierReceipt, SupplierReceipt.receipt_no, REFERENCES['receipt']),
            'work_order': (WorkOrder, WorkOrder.work_order_no, REFERENCES['work_order']), 'finished_lot': (MaterialLot, MaterialLot.lot_no, REFERENCES['finished_lot']),
            'inspection': (QualityInspection, QualityInspection.inspection_no, REFERENCES['inspection']), 'sales_order': (SalesOrder, SalesOrder.sales_order_no, REFERENCES['sales_order']), 'shipment': (Shipment, Shipment.shipment_no, REFERENCES['shipment']),
        }
        completed = [key for key, (model, field, value) in checks.items() if await DemoService._one(db, model, field, value)]
        missing = [key for key in checks if key not in completed]
        raw = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, REFERENCES['raw_lot'])
        finished = await DemoService._one(db, MaterialLot, MaterialLot.lot_no, REFERENCES['finished_lot'])
        if raw and finished and await db.scalar(select(TraceRelation.id).where(TraceRelation.source_id == raw.id, TraceRelation.target_id == finished.id, TraceRelation.deleted == 0)):
            completed.append('trace_relation')
        else:
            missing.append('trace_relation')
        return ManufacturingDemoVerifyResult(passed=not missing, completed_steps=completed, missing_steps=missing, references=REFERENCES)

    @staticmethod
    async def status(db: AsyncSession) -> ManufacturingDemoStatus:
        run = await db.scalar(select(ManufacturingDemoRun).where(ManufacturingDemoRun.scenario_code == SCENARIO, ManufacturingDemoRun.deleted == 0))
        return ManufacturingDemoStatus(run=ManufacturingDemoRunDetail.model_validate(run) if run else None, verification=await DemoService.verify(db))

    @staticmethod
    async def sales_order_driven_status(db: AsyncSession) -> ManufacturingDemoStatus:
        run = await db.scalar(
            select(ManufacturingDemoRun).where(
                ManufacturingDemoRun.scenario_code == SALES_ORDER_DRIVEN_SCENARIO,
                ManufacturingDemoRun.deleted == 0,
            )
        )
        return ManufacturingDemoStatus(
            run=ManufacturingDemoRunDetail.model_validate(run) if run else None,
            verification=await DemoService.verify_sales_order_driven(db),
        )


demo_service = DemoService()
