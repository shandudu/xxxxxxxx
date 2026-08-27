# RMA 售后处理执行闭环 PRD

版本：V1.0  
适用项目：`fastapi_best_architecture`（MySQL）

## 1. 目标

将 RMA 上登记的退款、换货、维修、报废处理结果转成可执行、可审计的售后执行单。执行单必须具备明确状态、幂等副作用和操作日志，避免只记录备注而没有实际业务动作。

## 2. 流程

```text
RMA CLOSED/RESOLVED
  → 创建售后执行单 DRAFT
  → 审批 APPROVED
  → 开始执行 IN_PROGRESS
  → 退款：完成财务处理记录
  → 换货：发出替换物料，写 SHIPMENT 库存流水
  → 维修：创建售后维修任务，完成维修后回写结果
  → 报废：扣减退货隔离库存，写 SCRAP 库存流水
  → COMPLETED
```

## 3. 数据对象

- `erp_customer_after_sales_order`：执行单主表，关联 RMA、投诉、客户、原退货物料/批次、处理类型、数量、库存流水和执行状态。
- `erp_customer_after_sales_repair_task`：维修类型专用任务，记录维修描述、开始/完成时间和维修结果。
- `erp_customer_after_sales_audit`：状态变更及库存流水/维修任务等副作用审计。

处理类型沿用 RMA 的 `REFUND`、`REPLACEMENT`、`REPAIR`、`SCRAP`；`NO_DEFECT` 不生成执行单。

## 4. 业务规则

1. 售后执行单必须来源于已存在的 RMA，且 RMA 至少处于 `RESOLVED`；同一个 RMA 同一种处理类型只能有一张有效执行单。
2. 状态只能按 `DRAFT → APPROVED → IN_PROGRESS → COMPLETED` 流转，任何状态变更写审计记录；已完成或取消的执行单不可重复执行。
3. 换货必须指定替换物料和替换数量，执行时写负库存 `SHIPMENT` 流水；库存不足时整个事务失败。
4. 报废执行时从退货批次/库位扣减库存，写负库存 `SCRAP` 流水；退款不产生库存变更。
5. 维修执行时创建唯一维修任务；维修任务完成后才允许执行单完成。
6. 所有库存副作用使用 `AFTER_SALES:{order_id}` 幂等键，重复调用不得重复扣库存。

## 5. API

- `GET /api/v1/mes/quality/after-sales-orders`
- `POST /api/v1/mes/quality/customer-returns/{return_id}/after-sales-orders`
- `POST /api/v1/mes/quality/after-sales-orders/{id}/approve`
- `POST /api/v1/mes/quality/after-sales-orders/{id}/start`
- `POST /api/v1/mes/quality/after-sales-orders/{id}/complete`
- `POST /api/v1/mes/quality/after-sales-orders/{id}/cancel`
- `GET /api/v1/mes/quality/after-sales-orders/{id}/repair-task`
- `POST /api/v1/mes/quality/after-sales-orders/{id}/repair-task/complete`

## 6. 验收标准

- 四类处理均可创建、审批、执行、完成，状态和审计记录完整。
- 换货/报废在 MySQL 中可查到对应库存流水，重复执行不重复扣减。
- 维修必须经过维修任务完成才能关闭执行单。
- RMA、投诉、执行单、库存流水/维修任务可互相追溯。
- Alembic 升级可重复执行，按维修任务→审计→执行单顺序回滚成功。
