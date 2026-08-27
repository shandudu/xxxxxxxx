from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped,mapped_column
from backend.common.model import Base,UniversalText,id_key
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
class OperationMaterialPlan(Base):
    """Independent BOM-to-routing allocation plan."""
    __tablename__='mes_operation_material_plan'
    __table_args__=(sa.ForeignKeyConstraint(['bom_id'],['mes_bom.id'],name='fk_operation_material_plan_bom'),sa.ForeignKeyConstraint(['routing_id'],['mes_routing.id'],name='fk_operation_material_plan_routing'),sa.UniqueConstraint('plan_code','deleted',name='uk_mes_operation_material_plan_code'),sa.UniqueConstraint('bom_id','routing_id','deleted',name='uk_mes_operation_material_plan_pair'),{'comment':'MES operation material allocation plans'})
    id:Mapped[id_key]=mapped_column(init=False);plan_code:Mapped[str]=mapped_column(sa.String(80));bom_id:Mapped[int]=mapped_column(sa.BigInteger);routing_id:Mapped[int]=mapped_column(sa.BigInteger);status:Mapped[OperationMaterialPlanStatus]=mapped_column(sa.String(20),default=OperationMaterialPlanStatus.DRAFT,server_default=OperationMaterialPlanStatus.DRAFT.value);remark:Mapped[str|None]=mapped_column(UniversalText,default=None)
class OperationMaterialRequirement(Base):
    """Maps one BOM component quantity to a routing operation."""
    __tablename__='mes_operation_material_requirement'
    __table_args__=(sa.ForeignKeyConstraint(['plan_id'],['mes_operation_material_plan.id'],name='fk_operation_material_requirement_plan'),sa.ForeignKeyConstraint(['bom_item_id'],['mes_bom_item.id'],name='fk_operation_material_requirement_bom_item'),sa.ForeignKeyConstraint(['routing_operation_id'],['mes_routing_operation.id'],name='fk_operation_material_requirement_operation'),sa.UniqueConstraint('plan_id','bom_item_id','routing_operation_id','deleted',name='uk_mes_operation_material_requirement'),{'comment':'MES operation material requirements'})
    id:Mapped[id_key]=mapped_column(init=False);plan_id:Mapped[int]=mapped_column(sa.BigInteger);bom_item_id:Mapped[int]=mapped_column(sa.BigInteger);routing_operation_id:Mapped[int]=mapped_column(sa.BigInteger);quantity:Mapped[Decimal]=mapped_column(sa.Numeric(18,6));remark:Mapped[str|None]=mapped_column(UniversalText,default=None)
