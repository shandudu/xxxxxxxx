# 供应商交期协同、采购 OTIF 与缺料影响分析 PRD V1.0

## 1. 目标

将采购订单从“下单”推进到“供应商承诺、到货、缺料影响可见”，形成：

> MRP 缺口 → 采购建议 → 供应商确认交期 → 收货 → 采购 OTIF → 销售延期影响

## 2. 业务规则

### 2.1 交期协同

- 采购订单行记录内部要求交期 `requested_delivery_at`。
- 供应商确认时记录承诺交期 `supplier_confirmed_delivery_at`。
- 没有供应商确认日期时，以内部要求交期作为 OTIF 基准。
- 采购订单确认后才能收货；供应商承诺日期允许在订单确认时补录或更新。

### 2.2 采购 OTIF

- 实际到货日期取覆盖订单行全部数量的最后一张收货单创建时间。
- `OTIF`：足量到货且实际日期不晚于承诺交期。
- `LATE`：足量到货但超过承诺交期。
- `OPEN`：未足量到货且尚未超期。
- `LATE_AND_NOT_IN_FULL`：已超期且未足量到货。
- 延期原因优先标记为 `SHORTAGE_IMPACT`（已经影响销售缺料），否则为 `SUPPLIER`。

### 2.3 缺料影响

- 按采购物料聚合当前销售订单 ATP/CTP 快照中的缺料数量和受影响订单数。
- 同时读取最近一次完成的 MRP 未覆盖缺口，作为计划侧缺料参考。
- 采购 OTIF 看板显示供应商、物料、未到数量、延期天数、受影响销售订单数和缺料量。

## 3. 接口与页面

- `POST /api/v1/erp/purchasing/orders/{order_id}/confirm`：确认采购订单，可带供应商承诺交期；
- `GET /api/v1/erp/purchasing/delivery/dashboard`：采购 OTIF 与供应商汇总；
- `POST /api/v1/erp/purchasing/delivery/recalculate`：重算采购交付快照；
- `GET /api/v1/erp/purchasing/orders/{order_id}/delivery-performance`：采购订单行交付明细；
- 前端 `/erp/purchasing/delivery`：供应商交期协同、采购 OTIF 和缺料影响看板。

## 4. 验收标准

- MRP 释放的采购建议带入需求日期作为采购要求交期。
- 采购确认后可保存供应商承诺日期。
- 收货后自动刷新采购 OTIF，足量按期到货为 OTIF。
- 延期采购订单能显示缺料影响数量和销售订单数。
- MySQL 迁移可升级/回滚，后端测试、前端类型检查和构建通过。
