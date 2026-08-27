from collections.abc import Sequence
from decimal import Decimal
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.common.exception import errors
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom,BomItem
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
from backend.plugin.operation_material.model import OperationMaterialPlan,OperationMaterialRequirement
from backend.plugin.operation_material.schema.operation_material import CreateOperationMaterialPlan,CreateOperationMaterialRequirement,PlanDetail,PlanValidation,RequirementDetail
from backend.plugin.routing.enums import RoutingStatus
from backend.plugin.routing.model import Routing,RoutingOperation
class OperationMaterialService:
 @staticmethod
 async def requirements(db,plan_id):return (await db.scalars(select(OperationMaterialRequirement).where(OperationMaterialRequirement.plan_id==plan_id,OperationMaterialRequirement.deleted==0).order_by(OperationMaterialRequirement.id))).all()
 @staticmethod
 def detail(plan,rows):
  d=PlanDetail.model_validate(plan);d.requirements=[RequirementDetail.model_validate(x) for x in rows];return d
 @staticmethod
 async def get_model(db,plan_id,lock=False):
  stmt=select(OperationMaterialPlan).where(OperationMaterialPlan.id==plan_id,OperationMaterialPlan.deleted==0)
  if lock:stmt=stmt.with_for_update()
  plan=await db.scalar(stmt)
  if not plan:raise errors.NotFoundError(msg='OPERATION_MATERIAL_PLAN_NOT_FOUND')
  return plan
 @staticmethod
 async def list_plans(db)->Sequence[OperationMaterialPlan]:return (await db.scalars(select(OperationMaterialPlan).where(OperationMaterialPlan.deleted==0).order_by(OperationMaterialPlan.created_time.desc()))).all()
 @staticmethod
 async def get(db,plan_id):
  p=await OperationMaterialService.get_model(db,plan_id);return OperationMaterialService.detail(p,await OperationMaterialService.requirements(db,p.id))
 @staticmethod
 async def create(db:AsyncSession,obj:CreateOperationMaterialPlan):
  bom=await db.scalar(select(Bom).where(Bom.id==obj.bom_id,Bom.deleted==0));routing=await db.scalar(select(Routing).where(Routing.id==obj.routing_id,Routing.deleted==0))
  if not bom or not routing or bom.product_material_id!=routing.product_material_id:raise errors.ConflictError(msg='BOM_ROUTING_PRODUCT_MISMATCH')
  if await db.scalar(select(OperationMaterialPlan.id).where(((OperationMaterialPlan.plan_code==obj.plan_code)|((OperationMaterialPlan.bom_id==obj.bom_id)&(OperationMaterialPlan.routing_id==obj.routing_id))),OperationMaterialPlan.deleted==0)):raise errors.ConflictError(msg='OPERATION_MATERIAL_PLAN_EXISTS')
  p=OperationMaterialPlan(**obj.model_dump());db.add(p);await db.flush();return OperationMaterialService.detail(p,[])
 @staticmethod
 async def add_requirement(db:AsyncSession,plan_id:int,obj:CreateOperationMaterialRequirement):
  p=await OperationMaterialService.get_model(db,plan_id,True)
  if p.status!=OperationMaterialPlanStatus.DRAFT:raise errors.ConflictError(msg='PLAN_NOT_DRAFT')
  bi=await db.scalar(select(BomItem).where(BomItem.id==obj.bom_item_id,BomItem.bom_id==p.bom_id,BomItem.deleted==0));ro=await db.scalar(select(RoutingOperation).where(RoutingOperation.id==obj.routing_operation_id,RoutingOperation.routing_id==p.routing_id,RoutingOperation.deleted==0))
  if not bi:raise errors.NotFoundError(msg='PLAN_BOM_ITEM_NOT_FOUND')
  if not ro:raise errors.NotFoundError(msg='PLAN_ROUTING_OPERATION_NOT_FOUND')
  if await db.scalar(select(OperationMaterialRequirement.id).where(OperationMaterialRequirement.plan_id==p.id,OperationMaterialRequirement.bom_item_id==bi.id,OperationMaterialRequirement.routing_operation_id==ro.id,OperationMaterialRequirement.deleted==0)):raise errors.ConflictError(msg='OPERATION_MATERIAL_REQUIREMENT_EXISTS')
  row=OperationMaterialRequirement(plan_id=p.id,**obj.model_dump());db.add(row);await db.flush();return row
 @staticmethod
 async def update_requirement(db,plan_id,row_id,obj):
  p=await OperationMaterialService.get_model(db,plan_id,True)
  if p.status!=OperationMaterialPlanStatus.DRAFT:raise errors.ConflictError(msg='PLAN_NOT_DRAFT')
  row=await db.scalar(select(OperationMaterialRequirement).where(OperationMaterialRequirement.id==row_id,OperationMaterialRequirement.plan_id==plan_id,OperationMaterialRequirement.deleted==0).with_for_update())
  if not row:raise errors.NotFoundError(msg='OPERATION_MATERIAL_REQUIREMENT_NOT_FOUND')
  bi=await db.scalar(select(BomItem.id).where(BomItem.id==obj.bom_item_id,BomItem.bom_id==p.bom_id,BomItem.deleted==0));ro=await db.scalar(select(RoutingOperation.id).where(RoutingOperation.id==obj.routing_operation_id,RoutingOperation.routing_id==p.routing_id,RoutingOperation.deleted==0))
  if not bi or not ro:raise errors.ConflictError(msg='REQUIREMENT_NOT_IN_PLAN_VERSIONS')
  for k,v in obj.model_dump().items():setattr(row,k,v)
  await db.flush();return row
 @staticmethod
 async def delete_requirement(db,plan_id,row_id):
  p=await OperationMaterialService.get_model(db,plan_id,True)
  if p.status!=OperationMaterialPlanStatus.DRAFT:raise errors.ConflictError(msg='PLAN_NOT_DRAFT')
  row=await db.scalar(select(OperationMaterialRequirement).where(OperationMaterialRequirement.id==row_id,OperationMaterialRequirement.plan_id==plan_id,OperationMaterialRequirement.deleted==0))
  if not row:raise errors.NotFoundError(msg='OPERATION_MATERIAL_REQUIREMENT_NOT_FOUND')
  row.deleted=row.id;return None
 @staticmethod
 async def validate(db,plan_id):
  p=await OperationMaterialService.get_model(db,plan_id);items=(await db.scalars(select(BomItem).where(BomItem.bom_id==p.bom_id,BomItem.deleted==0))).all();rows=await OperationMaterialService.requirements(db,p.id);errors_list=[];warnings=[]
  sums={}
  for r in rows:sums[r.bom_item_id]=sums.get(r.bom_item_id,Decimal('0'))+r.quantity
  for item in items:
   allocated=sums.get(item.id,Decimal('0'))
   if allocated==0 and not item.is_optional:errors_list.append(f'BOM item {item.line_no} is not allocated')
   elif allocated!=item.quantity:warnings.append(f'BOM item {item.line_no} allocated {allocated}, BOM quantity {item.quantity}')
  return PlanValidation(valid=not errors_list,errors=errors_list,warnings=warnings,bom_item_count=len(items),allocated_item_count=len(sums))
 @staticmethod
 async def status(db,plan_id,target):
  p=await OperationMaterialService.get_model(db,plan_id,True)
  if target==OperationMaterialPlanStatus.ACTIVE:
   result=await OperationMaterialService.validate(db,p.id)
   if not result.valid:raise errors.ConflictError(msg='OPERATION_MATERIAL_PLAN_INVALID')
   bom=await db.scalar(select(Bom).where(Bom.id==p.bom_id,Bom.deleted==0));routing=await db.scalar(select(Routing).where(Routing.id==p.routing_id,Routing.deleted==0))
   if not bom or bom.status!=BomStatus.ACTIVE or not routing or routing.status!=RoutingStatus.ACTIVE:raise errors.ConflictError(msg='BOM_OR_ROUTING_NOT_ACTIVE')
  p.status=target;await db.flush();return await OperationMaterialService.get(db,p.id)
operation_material_service=OperationMaterialService()
