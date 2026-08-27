# 销售/采购自动开票、三单匹配、收付款计划与银行对账 PRD v1.0

## 1. 目标

把销售出库、采购收货和财务单据串成自动闭环，减少重复录入，并通过三单匹配、付款计划和银行流水对账控制收入确认、采购付款和资金风险。

## 2. 业务规则

- 销售自动开票：按已过账发货单明细数量 × 销售订单单价汇总净额，按税率计算税额和价税合计；同一发货单只能生成一张有效应收发票。
- 采购自动开票：按供应商收货单明细数量 × 采购订单单价汇总净额；同一收货单只能生成一张有效应付发票。
- 自动开票同时生成一条收付款计划，计划金额等于价税合计，支持部分核销、已结清和逾期状态。
- 三单匹配：采购订单行、供应商收货行、应付发票必须属于同一采购链路；数量差异和价格差异分开计算，状态为 MATCHED、QUANTITY_VARIANCE 或 PRICE_VARIANCE。
- 银行对账：导入银行流水后，按方向、金额、参考号匹配客户收款或供应商付款；支持部分匹配、重复匹配拦截和自动匹配。

## 3. API

- `POST /api/v1/erp/finance/ar/invoices/from-shipments/{shipment_id}`
- `POST /api/v1/erp/finance/ap/invoices/from-receipts/{receipt_id}`
- `GET /api/v1/erp/finance/payment-plans`
- `POST /api/v1/erp/finance/purchase/three-way-match`
- `POST/GET /api/v1/erp/finance/bank/statements`
- `POST /api/v1/erp/finance/bank/reconcile`
- `POST /api/v1/erp/finance/bank/statements/{id}/auto-reconcile`

## 4. 数据模型

- `erp_payment_plan`：应收/应付计划和结算进度。
- `erp_three_way_match`：订单、收货、发票匹配结果和差异。
- `erp_bank_statement`：银行流水导入记录。
- `erp_bank_reconciliation`：流水与收付款单的匹配关系。
- 应收/应付发票增加来源唯一约束，保证自动开票幂等。

## 5. 验收与回滚

- 重复调用自动开票返回原发票，不生成重复应收/应付。
- 自动开票金额与来源单据明细金额一致，税额独立列示。
- 三单匹配能识别数量差异和价格差异。
- 同一银行流水不能被重复匹配超过流水金额；参考号和金额一致时可自动匹配。
- 验收脚本默认在事务内执行并回滚；迁移 `b2d4f6a8c0e3` 可回滚新增自动化表及来源唯一约束。
