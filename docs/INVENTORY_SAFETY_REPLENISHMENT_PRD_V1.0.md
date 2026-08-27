# 安全库存、补货点与自动补货建议 PRD V1.0

## 1. 目标

把库存、销售需求、采购在途和生产在制转化为可执行补货建议：

> 库存策略 → 可用库存与预计需求 → 补货缺口 → 采购/生产建议 → ATP/CTP 重算

## 2. 业务规则

### 2.1 库存策略

- 每个物料可维护安全库存、补货点、最高库存、采购/生产提前期、最小补货量。
- 可用库存 = 库存数量 - 已预留数量。
- 预计可用 = 可用库存 + 已确认采购在途 + 未完工生产在制 - 确认中销售订单剩余需求。
- 当预计可用低于补货点时生成补货建议。
- 建议数量 = max(最高库存 - 预计可用, 安全库存 - 预计可用, 最小补货量)。
- 可采购且不可生产的物料生成采购建议；可生产物料优先生成生产建议。

### 2.2 建议生命周期

`SUGGESTED → FIRM → RELEASED`，也支持 `CANCELLED`。

- `SUGGESTED`：系统计算产生，可重复计算但不覆盖已固定建议。
- `FIRM`：计划员确认建议。
- `RELEASED`：采购建议转采购订单草稿，生产建议转生产工单草稿。
- 释放后自动刷新销售订单 ATP/CTP。

### 2.3 预警

- `SHORTAGE`：预计可用低于安全库存。
- `REORDER`：预计可用低于补货点但尚未低于安全库存。
- `COVERED`：现有供给可覆盖策略目标。

## 3. 接口与页面

- `PUT /api/v1/mes/inventory/policies/{material_id}`：维护物料库存策略；
- `POST /api/v1/mes/inventory/replenishment/generate`：生成补货建议；
- `GET /api/v1/mes/inventory/replenishment/dashboard`：补货与缺口看板；
- `POST /api/v1/mes/inventory/replenishment/{id}/firm`：固定建议；
- `POST /api/v1/mes/inventory/replenishment/{id}/release`：转采购/生产业务单据；
- 前端 `/mes/inventory/replenishment`：策略、建议、缺口和执行状态。

## 4. 验收标准

- 可用库存、采购在途、生产在制和销售需求计算正确。
- 低于补货点时生成正确建议数量和建议类型。
- 建议固定、释放后状态和正式单据编号可追溯。
- 释放后 ATP/CTP 自动重算。
- MySQL 迁移可升级/回滚，后端、前端和补货回归验证通过。
