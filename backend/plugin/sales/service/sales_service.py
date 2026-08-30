from collections.abc import Sequence
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.customer.enums import CooperationStatus,CustomerStatus
from backend.plugin.customer.model import Customer
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.service import inventory_service
from backend.plugin.material.enums import MaterialStatus,UnitStatus
from backend.plugin.material.model import Material,UnitOfMeasure
from backend.plugin.sales.enums import SalesOrderStatus,ShipmentStatus
from backend.plugin.sales.model import SalesOrder,SalesOrderLine,Shipment,ShipmentLine
from backend.plugin.sales.schema.sales import CreateSalesOrder,CreateShipment,SalesOrderDetail,SalesOrderLineDetail,ShipmentDetail,ShipmentLineDetail
from backend.plugin.trace.enums import QualityStatus
from backend.plugin.trace.model import MaterialLot
from backend.utils.timezone import timezone

class SalesService:
    @staticmethod
    def operator_id():
        try:return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):return None
    @staticmethod
    async def order_lines(db:AsyncSession,order_id:int,lock:bool=False):
        stmt=select(SalesOrderLine).where(SalesOrderLine.sales_order_id==order_id,SalesOrderLine.deleted==0).order_by(SalesOrderLine.line_no)
        if lock:stmt=stmt.with_for_update()
        return (await db.scalars(stmt)).all()
    @staticmethod
    async def get_order_model(db:AsyncSession,order_id:int,lock:bool=False):
        stmt=select(SalesOrder).where(SalesOrder.id==order_id,SalesOrder.deleted==0)
        if lock:stmt=stmt.with_for_update()
        order=await db.scalar(stmt)
        if not order:raise errors.NotFoundError(msg='SALES_ORDER_NOT_FOUND')
        return order
    @staticmethod
    def detail(order,lines):
        d=SalesOrderDetail.model_validate(order);d.lines=[SalesOrderLineDetail.model_validate(x) for x in lines];return d
    @staticmethod
    async def list_orders(db:AsyncSession,status:str|None=None)->Sequence[SalesOrder]:
        stmt=select(SalesOrder).where(SalesOrder.deleted==0)
        if status:stmt=stmt.where(SalesOrder.status==status)
        return (await db.scalars(stmt.order_by(SalesOrder.created_time.desc(),SalesOrder.id.desc()))).all()
    @staticmethod
    async def get_order(db:AsyncSession,order_id:int):
        order=await SalesService.get_order_model(db,order_id);return SalesService.detail(order,await SalesService.order_lines(db,order.id))
    @staticmethod
    async def create_order(db:AsyncSession,obj:CreateSalesOrder):
        customer=await db.scalar(select(Customer).where(Customer.id==obj.customer_id,Customer.deleted==0))
        if not customer or customer.status!=CustomerStatus.ACTIVE or customer.cooperation_status!=CooperationStatus.NORMAL or not customer.sales_enabled:raise errors.ConflictError(msg='CUSTOMER_NOT_SALES_ENABLED')
        number=(obj.sales_order_no or f'SO-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper()
        if await db.scalar(select(SalesOrder.id).where(SalesOrder.sales_order_no==number,SalesOrder.deleted==0)):raise errors.ConflictError(msg='SALES_ORDER_NO_EXISTS')
        order=SalesOrder(sales_order_no=number,customer_id=customer.id,customer_code_snapshot=customer.customer_code,customer_name_snapshot=customer.customer_name,currency=obj.currency.upper(),requested_delivery_at=obj.requested_delivery_at,remark=obj.remark);db.add(order);await db.flush();lines=[]
        for no,item in enumerate(obj.lines,1):
            material=await db.scalar(select(Material).where(Material.id==item.material_id,Material.deleted==0));unit=await db.scalar(select(UnitOfMeasure).where(UnitOfMeasure.id==material.base_unit_id,UnitOfMeasure.deleted==0)) if material else None
            if not material or material.status!=MaterialStatus.ACTIVE or not material.sellable or not unit or unit.status!=UnitStatus.ACTIVE:raise errors.ConflictError(msg='MATERIAL_NOT_SELLABLE')
            line=SalesOrderLine(sales_order_id=order.id,line_no=no,material_id=material.id,unit_id=unit.id,ordered_quantity=item.ordered_quantity,unit_price=item.unit_price,material_code_snapshot=material.material_code,material_name_snapshot=material.material_name,unit_code_snapshot=unit.unit_code);db.add(line);lines.append(line)
        await db.flush();return SalesService.detail(order,lines)
    @staticmethod
    async def transition(db:AsyncSession,order_id:int,action:str):
        order=await SalesService.get_order_model(db,order_id,True)
        if action=='confirm':
            if order.status!=SalesOrderStatus.DRAFT:raise errors.ConflictError(msg='SALES_ORDER_NOT_DRAFT')
            order.status=SalesOrderStatus.CONFIRMED
        else:
            if order.status not in (SalesOrderStatus.DRAFT,SalesOrderStatus.CONFIRMED):raise errors.ConflictError(msg='SALES_ORDER_NOT_CANCELLABLE')
            order.status=SalesOrderStatus.CANCELLED
        await db.flush();return await SalesService.get_order(db,order.id)
    @staticmethod
    async def create_shipment(db:AsyncSession,obj:CreateShipment):
        order=await SalesService.get_order_model(db,obj.sales_order_id,True)
        if order.status not in (SalesOrderStatus.CONFIRMED,SalesOrderStatus.PARTIALLY_SHIPPED):raise errors.ConflictError(msg='SALES_ORDER_NOT_SHIPPABLE')
        customer=await db.scalar(select(Customer).where(Customer.id==order.customer_id,Customer.deleted==0))
        if not customer or not customer.shipment_enabled:raise errors.ConflictError(msg='CUSTOMER_SHIPMENT_DISABLED')
        number=(obj.shipment_no or f'SHP-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:6]}').upper();shipment=Shipment(shipment_no=number,sales_order_id=order.id,customer_id=order.customer_id,customer_code_snapshot=order.customer_code_snapshot,customer_name_snapshot=order.customer_name_snapshot,remark=obj.remark);db.add(shipment);await db.flush();lines=[]
        ids=[x.sales_order_line_id for x in obj.lines]
        if len(ids)!=len(set(ids)):raise errors.RequestError(msg='DUPLICATE_SALES_ORDER_LINE')
        for item in obj.lines:
            line=await db.scalar(select(SalesOrderLine).where(SalesOrderLine.id==item.sales_order_line_id,SalesOrderLine.deleted==0).with_for_update())
            if not line or line.sales_order_id!=order.id:raise errors.NotFoundError(msg='SALES_ORDER_LINE_NOT_FOUND')
            if line.shipped_quantity+item.quantity>line.ordered_quantity:raise errors.ConflictError(msg='SHIPMENT_QUANTITY_EXCEEDS_REMAINING')
            material=await db.scalar(select(Material).where(Material.id==line.material_id,Material.deleted==0))
            allocations=[]
            if item.auto_fefo:
                if not material or not material.batch_control:raise errors.ConflictError(msg='FEFO_REQUIRES_BATCH_CONTROL')
                from backend.plugin.inventory.service.shelf_life_service import shelf_life_service
                await shelf_life_service.sync_expiry_alerts(db)
                candidates=await shelf_life_service.fefo_candidates(db,material_id=line.material_id,warehouse_id=item.warehouse_id,quantity=item.quantity,lock=True)
                allocations=[(candidate.lot_id,candidate.location_id,candidate.allocated_quantity,candidate.lot_no) for candidate in candidates]
            else:
                lot=None
                if item.lot_id:
                    lot=await db.scalar(select(MaterialLot).where(MaterialLot.id==item.lot_id,MaterialLot.deleted==0))
                    if not lot or lot.material_id!=line.material_id:raise errors.ConflictError(msg='LOT_MATERIAL_MISMATCH')
                    if lot.quality_status!=QualityStatus.PASS:raise errors.ConflictError(msg='LOT_QUALITY_NOT_PASSED')
                if material and material.batch_control and not lot:raise errors.RequestError(msg='SHIPMENT_LOT_REQUIRED')
                allocations=[(lot.id if lot else None,item.location_id,item.quantity,lot.lot_no if lot else None)]
            for lot_id,location_id,allocated_quantity,lot_no in allocations:
                no=len(lines)+1
                tx=await inventory_service.post_transaction(db,idempotency_key=f'SHIPMENT:{shipment.id}:{no}',transaction_type=StockTransactionType.SHIPMENT,material_id=line.material_id,lot_id=lot_id,warehouse_id=item.warehouse_id,location_id=location_id,quantity_delta=-Decimal(allocated_quantity),reference_type='SHIPMENT',reference_id=shipment.id,reference_no=shipment.shipment_no,remark=obj.remark,operator_id=SalesService.operator_id())
                sl=ShipmentLine(shipment_id=shipment.id,sales_order_line_id=line.id,line_no=no,material_id=line.material_id,lot_id=lot_id,warehouse_id=item.warehouse_id,location_id=location_id,quantity=allocated_quantity,stock_transaction_id=tx.id,lot_no_snapshot=lot_no);db.add(sl);lines.append(sl)
            line.shipped_quantity+=item.quantity
        all_lines=await SalesService.order_lines(db,order.id);order.status=SalesOrderStatus.SHIPPED if all(x.shipped_quantity>=x.ordered_quantity for x in all_lines) else SalesOrderStatus.PARTIALLY_SHIPPED;await db.flush()
        from backend.plugin.sales.service.delivery_service import delivery_service
        await delivery_service.refresh_order(db, order.id)
        detail=ShipmentDetail.model_validate(shipment);detail.lines=[ShipmentLineDetail.model_validate(x) for x in lines];return detail
    @staticmethod
    async def deliver_shipment(db:AsyncSession,shipment_id:int,delivered_at=None):
        shipment=await db.scalar(select(Shipment).where(Shipment.id==shipment_id,Shipment.deleted==0).with_for_update())
        if not shipment:raise errors.NotFoundError(msg='SHIPMENT_NOT_FOUND')
        if shipment.status!=ShipmentStatus.POSTED:raise errors.ConflictError(msg='SHIPMENT_NOT_DELIVERABLE')
        shipment.status=ShipmentStatus.DELIVERED;shipment.delivered_at=delivered_at or timezone.now();await db.flush()
        from backend.plugin.sales.service.delivery_service import delivery_service
        await delivery_service.refresh_order(db, shipment.sales_order_id)
        lines=(await db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id==shipment.id,ShipmentLine.deleted==0).order_by(ShipmentLine.line_no))).all()
        detail=ShipmentDetail.model_validate(shipment);detail.lines=[ShipmentLineDetail.model_validate(x) for x in lines];return detail
    @staticmethod
    async def list_shipments(db:AsyncSession):return (await db.scalars(select(Shipment).where(Shipment.deleted==0).order_by(Shipment.created_time.desc()))).all()

sales_service=SalesService()
