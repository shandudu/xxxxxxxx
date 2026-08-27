from datetime import datetime
from decimal import Decimal
from pydantic import ConfigDict,Field,field_validator
from backend.common.schema import SchemaBase
from backend.plugin.operation_material.enums import OperationMaterialPlanStatus
class CreateOperationMaterialPlan(SchemaBase):
    plan_code:str=Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9_-]+$');bom_id:int=Field(ge=1);routing_id:int=Field(ge=1);remark:str|None=Field(default=None,max_length=500)
    @field_validator('plan_code',mode='before')
    @classmethod
    def code(cls,v):return str(v).strip().upper()
class CreateOperationMaterialRequirement(SchemaBase):
    bom_item_id:int=Field(ge=1);routing_operation_id:int=Field(ge=1);quantity:Decimal=Field(gt=0,max_digits=18,decimal_places=6);remark:str|None=Field(default=None,max_length=500)
class RequirementDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;plan_id:int;bom_item_id:int;routing_operation_id:int;quantity:Decimal;remark:str|None
class PlanDetail(SchemaBase):
    model_config=ConfigDict(from_attributes=True);id:int;plan_code:str;bom_id:int;routing_id:int;status:OperationMaterialPlanStatus;remark:str|None;created_time:datetime;requirements:list[RequirementDetail]=Field(default_factory=list)
class PlanValidation(SchemaBase):
    valid:bool;errors:list[str];warnings:list[str];bom_item_count:int;allocated_item_count:int
