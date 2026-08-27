# 设备维修成本闭环 PRD v1.0

## 目标

把设备故障维修从报修、停机、备件消耗、维修费用到财务凭证和停机成本分析串成可追溯闭环，确保库存与总账只过账一次。

## 业务流程

1. 维修人员在维修中工单上登记备件，系统校验物料、批次、仓库库位和可用库存，生成 `ISSUE` 库存交易；请求使用幂等键，重复提交不重复扣料。
2. 维修完成后选择开放会计期间执行“维修费用入账”。系统汇总备件成本与人工成本，生成借记 6602 维修费用、贷记 2202 应付账款的已过账凭证；同一维修单只能入账一次。
3. 成本分析按期间汇总维修工单、备件费、人工费、维修总费、停机分钟；调用方提供设备停机小时成本后计算停机机会成本。

## 规则与权限

- 备件领用仅允许 `IN_REPAIR` 或 `COMPLETED` 工单；取消/已报修工单不可领料。
- 费用入账仅允许已完成维修单和 OPEN 财务期间，金额必须大于零。
- 所有库存交易引用维修单号，凭证引用维修成本过账记录，支持审计追溯。
- 沿用 `mes:maintenance:view` 查看与 `mes:maintenance:repair` 执行权限。

## 接口

- `POST /api/v1/mes/maintenance/repairs/{repair_id}/parts`
- `GET /api/v1/mes/maintenance/repairs/{repair_id}/parts`
- `POST /api/v1/mes/maintenance/repairs/{repair_id}/cost/post`
- `GET /api/v1/mes/maintenance/repairs/cost-analysis?period_id=&hourly_downtime_cost=`

## 验收指标

- 库存余额、库存流水、维修备件明细三方数量与金额一致。
- 重试领料或费用入账接口不产生重复库存交易/凭证。
- 停机分钟取关联停机记录的关闭时长，停机成本 = 分钟 / 60 × 小时成本。
- MySQL Alembic 迁移可升级与回滚，前端维修成本分析页可查看汇总及明细。
