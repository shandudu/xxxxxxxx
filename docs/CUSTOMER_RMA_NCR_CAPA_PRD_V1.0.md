# 客户投诉与退货 RMA → NCR → CAPA/8D → 处理结果闭环 PRD

版本：V1.0  
适用项目：`fastapi_best_architecture`（MySQL）

## 1. 目标

把客户投诉、退货授权、退货入库检验、质量异常处置、CAPA/8D 改善和客户处理结果串成一条可追溯闭环。每个投诉只允许一个 RMA，退货实物必须形成库存流水和检验记录；发现不合格时自动生成 NCR，并要求 NCR/CAPA 完成后才允许对客户结案。

## 2. 业务流程

```text
客户投诉 OPEN
  → 创建 RMA RMA_CREATED
  → 退货接收 AUTHORIZED → RECEIVED（库存 CUSTOMER_RETURN 流水，批次 HOLD）
  → 退货检验 RECEIVED → INSPECTED
  → 合格：直接 RESOLVED
  → 不合格：自动创建 NCR NCR_OPEN → CAPA_IN_PROGRESS → NCR CLOSED
  → 客户处理结果 RESOLVED（退款/换货/维修/报废/无缺陷）
  → RMA CLOSED，投诉 CLOSED
```

## 3. 核心对象

- 客户投诉 `erp_customer_complaint`：客户、订单/发货/物料/批次快照，投诉描述，RMA/NCR/CAPA 关联和关闭信息。
- 退货 RMA `erp_customer_return`：投诉、客户、发货、状态、NCR 和客户处理结果。
- 退货明细 `erp_customer_return_line`：原发货行、物料/批次、仓库/库位、数量、库存流水和检验记录。

## 4. 状态与规则

投诉状态：`OPEN`、`RMA_CREATED`、`NCR_OPEN`、`CAPA_IN_PROGRESS`、`RESOLVED`、`CLOSED`、`CANCELLED`。  
RMA 状态：`DRAFT`、`AUTHORIZED`、`RECEIVED`、`INSPECTED`、`RESOLVED`、`CLOSED`、`CANCELLED`。

1. 一个投诉只能创建一个 RMA；订单/发货若指定，必须属于该客户，退货数量不能超过发货行数量。
2. 接收接口幂等：按 `CUSTOMER_RETURN:{return_id}:{line_id}` 写入 `CUSTOMER_RETURN` 正库存流水，重复调用不得重复入库，并将批次置为 `HOLD`。
3. 退货检验复用质量检验模型，结果为不合格且存在拒收数量时自动创建 NCR，并回写投诉与 RMA。
4. 存在 NCR 时，RMA 不得直接解决；NCR 必须关闭。若 NCR 关联 CAPA，则 CAPA 必须先通过有效性验证并关闭。
5. 只有 `RESOLVED` 的 RMA 可以关闭；RMA 关闭同时关闭投诉并记录关闭时间。

## 5. API

- `GET/POST /api/v1/mes/quality/customer-complaints`
- `GET/POST /api/v1/mes/quality/customer-returns`
- `POST /customer-returns/{id}/receive`
- `POST /customer-returns/{id}/inspect`
- `POST /customer-returns/{id}/resolve`
- `POST /customer-returns/{id}/close`

接口沿用质量域权限：查询权限 `mes:quality:view`，创建投诉/RMA 使用 `mes:quality:ncr`，接收/解决/关闭使用 `mes:quality:mrb:execute`，退货检验使用 `mes:quality:inspection`。

## 6. 验收标准

- 能从客户投诉创建 RMA，并从发货行带出物料/批次/仓库/库位。
- 接收 RMA 后 MySQL 库存流水、批次 HOLD 和幂等键可查询。
- 退货检验 FAIL 自动生成 NCR；NCR → MRB/返工/复检 → CAPA/8D → 验证关闭后，才能提交客户处理结果。
- 退款、换货、维修、报废、无缺陷五类处理结果均可审计；关闭后投诉和 RMA 状态均为 `CLOSED`。
- Alembic 升级可重复执行，回滚按明细表→RMA→投诉顺序成功。
