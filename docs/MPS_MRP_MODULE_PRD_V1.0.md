# MES + ERP MPS/MRP 模块 PRD V1.0

## 1. 建设目标

在现有物料、BOM、库存、采购、销售和生产模块之上建立计划层，形成以下闭环：

`独立需求 → MPS 确认 → MRP 多层展开与净额运算 → 计划订单 → 固定 → 正式采购单/生产工单`

计划模块只读取现有业务单据作为供给快照，不直接修改库存、采购订单或生产工单。正式单据只在用户执行“下达计划订单”后产生。

## 2. V1.0 范围

### 2.1 主生产计划 MPS

- 创建计划编号、名称和计划期间。
- 录入手工需求或预测需求。
- 导入已确认、未完全发货的销售订单剩余数量。
- 需求日期必须落在计划期间内。
- 草稿计划允许维护需求；确认后冻结需求，作为 MRP 输入快照。

### 2.2 物料需求运算 MRP

- 按需求日期和 MPS 行号顺序运算。
- 按“现存可用量 → 已确认采购未收量 → 草稿/已下达/执行中工单未完工量”依次抵扣。
- 只针对净需求生成计划订单。
- 可生产且存在生效 BOM 的物料生成计划生产订单，并继续展开非可选组件。
- 可采购物料生成计划采购订单。
- 不可生产且不可采购，或可生产但无有效 BOM 的物料，记录为未覆盖缺口。
- BOM 用量按基准数量、损耗率和固定损耗计算。
- 检测 BOM 循环引用和最大展开层级。
- 每次运算保存独立结果，不覆盖历史运行。

### 2.3 计划订单

- 计划订单支持 `PLANNED → FIRM → RELEASED`。
- 计划采购订单下达时必须选择供应商，生成正式采购订单草稿。
- 计划生产订单下达时使用指定或默认生效工艺路线，生成正式生产工单草稿。
- 正式单据编号和 ID 回写计划订单，避免重复下达。

## 3. 运算口径

### 3.1 可用库存

`可用库存 = 库存数量 - 已预留数量`

V1.0 按物料汇总所有仓库、库位和批次，不做仓库级净算。后续库存计划版本会加入计划仓、冻结量、批次有效期和调拨在途。

### 3.2 在途采购

仅统计状态为 `CONFIRMED` 或 `PARTIALLY_RECEIVED` 的采购订单：

`采购在途 = 订购数量 - 已收货数量`

当前采购订单尚无承诺交期，因此 V1.0 将所有有效在途视为计划期内可用。采购交期字段完善后应改为按日期桶抵扣。

### 3.3 在制供给

统计 `DRAFT`、`RELEASED` 和 `IN_PROGRESS` 工单：

`在制供给 = 计划数量 - 已完工数量`

### 3.4 提前期

V1.0 每次运行保存默认采购提前期和默认生产提前期：

`建议下达日期 = 需求日期 - 默认提前期`

后续将优先读取供应商物料提前期、物料采购提前期、工艺路线标准工时和工厂日历。

## 4. 状态机

- MPS：`DRAFT → CONFIRMED → CLOSED`
- MRP 运行：`RUNNING → COMPLETED / FAILED`
- 计划订单：`PLANNED → FIRM → RELEASED`，预留 `CANCELLED`
- 下达产生的采购订单和生产工单保持各自模块的原有状态机。

## 5. 数据实体

| 实体 | 表名 | 说明 |
| --- | --- | --- |
| MPS 计划 | `mes_mps_plan` | 计划期间和状态 |
| MPS 需求 | `mes_mps_demand` | 独立需求与来源快照 |
| MRP 运行 | `mes_mrp_run` | 运算参数、状态和统计 |
| MRP 需求 | `mes_mrp_requirement` | 毛需求、供给分配、净需求和缺口 |
| 计划订单 | `mes_planned_order` | 计划采购/生产及正式单据引用 |

所有实体使用物理外键保护核心引用，同时保留物料编码、名称和单位快照用于历史追溯。

## 6. API

- `GET/POST /api/v1/mes/planning/mps-plans`
- `GET /api/v1/mes/planning/mps-plans/{id}`
- `POST/DELETE /api/v1/mes/planning/mps-plans/{id}/demands`
- `POST /api/v1/mes/planning/mps-plans/{id}/import-sales-orders`
- `POST /api/v1/mes/planning/mps-plans/{id}/confirm`
- `GET/POST /api/v1/mes/planning/mrp-runs`
- `GET /api/v1/mes/planning/mrp-runs/{id}`
- `POST /api/v1/mes/planning/planned-orders/{id}/firm`
- `POST /api/v1/mes/planning/planned-orders/{id}/release`

## 7. 权限

- `mes:planning:view`
- `mes:planning:create`
- `mes:planning:confirm`
- `mes:planning:run`
- `mes:planning:firm`
- `mes:planning:release`

## 8. V1.0 不包含

- 安全库存、最大/最小库存和补货点。
- 固定批量、最小批量、批量倍数和经济订货批量。
- 替代料、联副产品、虚拟件和配置 BOM。
- 供应商配额和自动选供应商。
- 采购承诺交期和到货概率。
- 工厂工作日历、节假日、班次和能力约束。
- 跨工厂、跨组织和跨仓库的计划调拨。
- APS 有限能力排程。

上述项目作为 V1.1/V2.0 的明确增量范围，不在 V1.0 界面中伪装为已实现能力。

## 9. 验收标准

- 新表只通过 Alembic 增量迁移创建，不运行 `fba init`。
- 已确认 MPS 可执行多层 BOM 运算，并保留每层来源路径。
- 库存、采购在途和生产在制被顺序抵扣且不会重复使用。
- BOM 循环引用不会导致无限递归，运行结果标记为失败并记录原因。
- 计划采购订单可生成采购订单草稿；计划生产订单可生成生产工单草稿。
- 同一计划订单重复下达不会生成第二张正式单据。
- 后端测试、真实接口验收、前端类型检查和生产构建全部通过。
