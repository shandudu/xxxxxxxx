# 订单交期 ATP/CTP 与缺料/产能预警 PRD V1.0

## 1. 目标

在销售订单确认前后给出可承诺交期（ATP/CTP），将现有库存、未收采购、在制工单纳入供给计算，提前暴露缺料和产能风险。

## 2. 计算规则

- ATP = 当前库存数量 - 已预留数量，按物料汇总。
- CTP = ATP + 已确认/部分收货采购未收数量 + 已释放/生产中工单未完工数量。
- 剩余需求 = 订单数量 - 已发货数量。
- `COMMITTABLE`：供给覆盖剩余需求；`SHORTAGE`：ATP/采购/生产合计仍有缺口；`CAPACITY_RISK`：依赖生产且临近交期；`DELAYED`：承诺日期晚于客户要求日期。
- 默认要求交期为订单创建后 7 天，可在销售订单录入时指定。

## 3. 接口与页面

- `GET /api/v1/erp/sales/promise/dashboard`
- `POST /api/v1/erp/sales/orders/{id}/promise/assess`
- `GET /api/v1/erp/sales/orders/{id}/promise`
- 销售订单页展示 ATP/CTP、承诺日期、缺料数量、产能缺口和风险状态。

## 4. 验收

查询结果可追溯到订单行；评估可重复执行并覆盖最新供给快照；MySQL 迁移支持回滚；缺料和产能风险可在看板汇总；后端全量测试、MySQL 基线和前端 typecheck/build 通过。
