# 财务月结关账、库存盘点差异、税务发票台账与现金流预测 PRD v1.0

## 目标

在现有 MySQL 财务插件上形成“计价—盘点—凭证—税务—资金—关账”的月度闭环，所有动作可追溯、可回滚，关账只允许通过阻断项检查的期间执行。

## 业务范围

1. 月结检查：库存计价、盘点任务、凭证借贷平衡、银行对账四项检查；前三项为阻断项，银行未对账为提示项。通过后将财务期间置为 CLOSED，并记录关闭时间。
2. 库存盘点：按仓库/库位/批次录入账面数与实盘数，自动计算数量和金额差异；过账时调用库存调整台账，使用幂等键避免重复调整。
3. 税务发票台账：从 AR 输出发票、AP 输入发票同步台账，保留发票方向、税率、税额、认证号和状态。
4. 现金流预测：以未结清收付款计划生成到期日预测，按流入/流出汇总净现金流，并支持重建。

## 权限与接口

- `erp:finance:close`：月结检查与关账
- `erp:finance:count`：盘点创建与差异过账
- `erp:finance:tax`：税务台账同步
- `erp:finance:cashflow`：现金流预测重建
- `POST /api/v1/erp/finance/periods/{id}/closing/check`
- `POST /api/v1/erp/finance/periods/{id}/closing/close`
- `POST /api/v1/erp/finance/inventory/counts`、`POST .../counts/{id}/post`
- `POST /api/v1/erp/finance/tax/invoices/sync`
- `POST /api/v1/erp/finance/cash-flow/forecast/rebuild`

## 验收标准

- 关账阻断项未通过时事务回滚且期间仍为 OPEN。
- 盘点差异过账产生一笔 `ADJUSTMENT` 库存交易，再次提交不会重复扣加库存。
- AR/AP 发票同步后分别形成 OUTPUT/INPUT 台账，金额与原发票一致。
- 现金流预测可重建，流入、流出、净额与未结算付款计划一致。
- MySQL Alembic 迁移可升级/降级，后端静态检查和前端构建通过。
