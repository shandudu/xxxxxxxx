# 固定资产全生命周期、折旧计提与自动凭证 PRD v1.0

## 目标

建立从固定资产购置入账到调拨、维修、折旧、报废的可追溯账务闭环，资产账面净值与总账凭证保持一致。

## 业务范围

1. 资产卡片：资产编号、类别、原值、残值率、使用年限、成本中心、供应商和来源信息。
2. 购置入账：创建资产时自动生成 `1601 固定资产 → 2202 应付账款` 凭证，并写入生命周期台账。
3. 调拨：变更成本中心，记录调出/调入成本中心和调拨日期，不改变资产净值。
4. 维修：登记维修供应商、金额和说明，自动生成维修费用凭证。
5. 折旧：按月、直线法计提，公式为 `(原值 - 残值) / 使用月数`，不超过账面净值；自动生成 `6602 折旧费用 → 1602 累计折旧` 凭证，同一资产同一期间幂等。
6. 报废：资产状态变更为 SCRAPPED，账面净值清零并生成资产处置损益凭证。

## 权限与接口

- `erp:finance:asset`：资产新增、调拨、维修、报废、折旧
- `POST/GET /api/v1/erp/finance/fixed-assets`
- `POST /api/v1/erp/finance/fixed-assets/{id}/transfer`
- `POST /api/v1/erp/finance/fixed-assets/{id}/maintenance`
- `POST /api/v1/erp/finance/fixed-assets/{id}/dispose`
- `POST /api/v1/erp/finance/fixed-assets/depreciation/run?period_id={id}`

## 验收标准

- 购置资产自动产生平衡凭证和 ACQUISITION 台账。
- 调拨只改变成本中心，维修和报废都有独立生命周期记录。
- 折旧重复执行不重复扣减净值、不重复生成凭证。
- 期间关账后禁止资产新增和折旧计提。
- 所有动作在 MySQL 事务中可回滚，迁移、静态检查和前端构建通过。
