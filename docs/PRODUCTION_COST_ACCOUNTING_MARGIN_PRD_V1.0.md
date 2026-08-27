# 生产成本核算、工单成本结转与产品/客户毛利 PRD v1.0

## 1. 目标

把采购入库、生产领料、报工工时、设备/制造费用、质量损失和销售出库统一为可追溯的成本事实，形成“期间口径 → 工单试算 → 财务结转 → 产品/客户毛利”的闭环。首期以 MySQL、CNY、实际领料 + 实际报工为主，支持后续扩展标准成本和多币种。

## 2. 业务口径

- 材料成本：成本期间内供应商收货数量 × 采购订单含税单价的加权平均；工单材料成本来自 `MaterialConsumption` 实际消耗，缺少采购价时显示未覆盖而不伪造金额。
- 人工成本：报工执行时长（结束时间 - 开始时间）× 期间人工小时率。
- 机器成本：执行时长 × 机器小时率。
- 制造费用：执行时长 × 制造费用小时率。
- 质量损失：报废数量 ×（材料成本 / 合格品与报废品总量），单独列示，避免隐藏在单位成本中。
- 工单总成本 = 材料 + 人工 + 机器 + 制造费用 + 质量损失；单位成本以合格数量为分母。
- 毛利：销售出库数量 × 销售订单单价 − 出库数量 × 已结转工单单位成本；同时返回成本覆盖率，禁止将未结转成本默认为“已核算”。

## 3. 核心流程

1. 财务建立成本期间，维护日期、人工/机器/制造费用小时率。
2. 期间内采购收货、生产领料和报工持续沉淀业务事实。
3. 成本员按工单试算，查看成本要素和来源明细；可重复试算，已结转工单幂等保护。
4. 工单完工并复核后执行结转，状态从 `CALCULATED` 变为 `POSTED`；期间关闭前不允许存在未结转记录。
5. 销售出库按产品或客户查看收入、销货成本、毛利、毛利率和成本覆盖率。

## 4. 数据模型与权限

- `erp_cost_period`：成本期间与费用率，状态 OPEN/CALCULATING/CLOSED。
- `erp_material_cost`：期间材料加权平均成本及来源数量/金额。
- `erp_work_order_cost`：工单成本汇总与结转状态。
- `erp_work_order_cost_line`：材料、人工、机器、制造费用、质量损失的来源追溯明细。
- 权限：`erp:costing:view`、`erp:costing:manage`、`erp:costing:calculate`、`erp:costing:post`、`erp:costing:close`。

## 5. API 与验收标准

- `GET/POST /api/v1/erp/costing/periods`
- `GET /api/v1/erp/costing/work-orders/{id}?period_id=`
- `POST /api/v1/erp/costing/work-orders/{id}/calculate`
- `POST /api/v1/erp/costing/work-orders/{id}/post`
- `POST /api/v1/erp/costing/periods/{id}/close`
- `GET /api/v1/erp/costing/margins?dimension=PRODUCT|CUSTOMER&period_id=`

验收：同一工单重复结转不重复记账；关闭期间拒绝重新计算；关闭期间前存在未结转工单时拒绝关闭；成本明细可追溯到领料/报工；产品与客户合计收入、成本、毛利与明细一致；成本覆盖率小于 100% 时前端明确标识。

## 6. 回滚与风险

迁移 `f8b1c3d5e7a9` 可回滚四张成本表；演示/自动化验收使用事务并回滚。成本期间关闭是业务闸门，生产、采购、销售原始单据不被修改；若采购价缺失只产生成本覆盖预警，不阻断业务单据。
