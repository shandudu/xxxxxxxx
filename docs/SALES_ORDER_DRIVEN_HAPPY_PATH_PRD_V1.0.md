# 销售订单驱动 MES + ERP Happy Path PRD V1.0

## 1. 业务目标

在现有 FBA 插件体系中验证一条真实的按需生产闭环：客户销售订单确认后，系统将需求导入 MPS/MRP，生成采购和生产计划订单，释放为采购订单与生产工单，完成收货、领料、生产报工、质量放行、成品入库、发货，并支持成品到原材料和原材料到客户的双向追溯。

本 PRD 是对 `MANUFACTURING_HAPPY_PATH_DEMO_PRD_V1.0.md` 的业务驱动扩展。已有业务模块继续作为唯一事实来源，不复制核心业务表，不绕过既有 Service 写库存或状态。

## 2. 范围

### 2.1 一期包含

```text
Customer
  ↓
Sales Order（确认）
  ↓
MPS Demand（来源为 SalesOrderLine）
  ↓
MRP Run
  ↓
Planned Order（PURCHASE / PRODUCTION）
  ↓
Purchase Order + Supplier Receipt
  ↓
Raw Material Lot / Inventory
  ↓
Work Order（冻结 BOM + Routing）
  ↓
Material Issue + Operation Execution
  ↓
Production Report + Finished Lot
  ↓
Final Inspection / PASS
  ↓
Shipment + Inventory Deduction
  ↓
Forward / Reverse Trace
```

### 2.2 明确不做

- 不实现新的 MRP 算法；复用 `planning` 插件现有净需求计算。
- 不实现高级 APS、有限产能排程、采购价格比选或财务结算。
- 不修改销售订单、采购订单、工单核心表来增加重复的业务状态字段。
- 不复制 C 盘 SQLite 项目的认证、模型或迁移。
- 不自动删除演示数据；重复执行必须幂等或明确报告冲突。

## 3. 现有能力与依赖

| 能力 | 现有来源 | 本期使用方式 |
| --- | --- | --- |
| 销售订单 | `sales` | 创建、确认、剩余量校验 |
| 需求导入 | `planning.import_sales_orders` | 以 `SalesOrderLine.id` 作为需求来源 |
| MRP | `planning.run_mrp` | 计算成品生产和原材料采购计划 |
| 计划释放 | `planning.release_planned_order` | 生成采购订单或生产工单 |
| 收货库存 | `purchasing` + `inventory` | 批次、库存流水、来料检验 |
| 生产执行 | `production` | 工单快照、领料、工序执行、报工 |
| 质量 | `quality` | IQC/FQC 与批次质量门禁 |
| 发货 | `sales.create_shipment` | PASS 批次扣库存 |
| 追溯 | `trace` | 上游到下游唯一方向关系 |

## 4. 核心业务规则

1. 只有 `CONFIRMED` 或 `PARTIALLY_SHIPPED` 销售订单允许导入 MPS；已发完的订单行不生成需求。
2. 同一个 MPS 计划中，同一销售订单行只能导入一次；重复调用返回已存在需求，不重复生成。
3. MRP 必须在 MPS `CONFIRMED` 后执行；MRP 失败时保留失败快照，不释放计划订单。
4. 计划订单释放必须幂等：已释放订单直接返回原采购订单/工单引用。
5. 采购计划订单必须明确供应商；生产计划订单必须找到 ACTIVE BOM 和 Routing，并冻结版本快照。
6. 采购收货数量不得超过采购订单剩余量；收货产生批次、库存入账和来料检验。
7. 生产领料只能使用当前工单需求允许的物料批次，库存不可变流水必须使用幂等键。
8. 生产报工产生的成品批次必须通过最终检验后才能发货；不合格批次保持 `HOLD`。
9. 发货数量不得超过销售订单未发数量，批次受控成品必须指定 `PASS` 批次。
10. 追溯关系统一保存为 `上游 → 下游`：原料批次 → 成品批次 → 序列号/发货；不保存重复反向边。
11. 每个步骤在同一数据库事务内调用既有 Service；跨步骤失败时记录失败步骤，不伪造已完成业务事实。

## 5. 编排接口

本期在现有 `demo` 插件中增加一个场景入口，不新建业务模块：

| 方法 | 地址 | 权限 | 作用 |
| --- | --- | --- | --- |
| POST | `/api/v1/mes/demo/sales-order-driven-happy-path/run` | `mes:demo:run` | 创建或续跑销售订单驱动闭环 |
| GET | `/api/v1/mes/demo/sales-order-driven-happy-path/status` | `mes:demo:view` | 返回步骤状态及业务单号 |
| POST | `/api/v1/mes/demo/sales-order-driven-happy-path/verify` | `mes:demo:view` | 只读校验需求、供应、生产、库存、质量、发货和追溯 |

编排接口只负责调用各模块 Service；业务状态转换、库存扣减、质量判定和追溯关系仍由原模块负责。

## 6. 演示运行记录

复用 `mes_demo_run`，通过不同 `scenario_code` 区分本场景：

```text
SALES_ORDER_DRIVEN_HAPPY_PATH
```

业务明细不写入 JSON。运行记录只保存运行状态、失败步骤和错误摘要；具体关系通过 MPS、MRP、计划订单和业务单据稳定 ID 追溯。

## 7. 验收标准

- 销售订单确认后可生成来源明确的 MPS Demand。
- MRP 能生成原材料采购计划订单和成品生产计划订单。
- 计划订单释放后能定位采购订单和生产工单。
- 采购收货、生产领料、报工、质检、发货均调用既有业务 Service。
- 重复运行不重复创建销售订单、计划订单、采购订单、工单、库存流水或发货单。
- 验证接口能检查：销售需求来源、计划供应、采购/生产来源引用、库存流水、质量状态、发货状态、正向和反向追溯。
- 后端服务/API 测试通过；MySQL 只读结构验证通过；前端类型检查和生产构建通过。

## 8. 失败与边界

| 场景 | 结果 |
| --- | --- |
| 销售订单未确认 | 返回 `SALES_ORDER_NOT_CONFIRMED_OR_NOT_FOUND` |
| 没有 ACTIVE BOM/Routing | MRP 或生产释放失败，不创建工单 |
| 没有可用供应商 | 采购计划订单保留为 `FIRM`，不释放采购单 |
| 库存不足 | 领料事务回滚，工单不伪造完成 |
| 质量未 PASS | 发货被质量门禁拒绝 |
| 重复执行 | 返回已有对象或已完成状态，不重复过账 |

## 9. Definition of Done

1. 本文件与现有 `demo`、`planning`、`sales`、`purchasing`、`production`、`quality`、`trace` 代码一致。
2. 新增场景入口和只读验证，不破坏原制造演示入口。
3. 至少覆盖正常路径、重复调用、未确认订单、无供应商、质量未放行和库存不足测试。
4. 所有修改集中在 F 项目，且没有删除用户已有文件。
