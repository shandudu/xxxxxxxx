# 预算管理、成本中心、费用报销与预算预警 PRD v1.0

## 目标

在现有财务期间、凭证、付款计划和成本核算基础上，建立“预算编制 → 审批 → 费用申请 → 预算占用 → 超额预警 → 凭证入账”的经营费用控制闭环。

## 核心业务

1. 成本中心：维护部门、工厂、项目等成本归属单元，支持上下级关系和负责人。
2. 预算管理：按财务期间、预算类型和成本中心编制预算，按会计科目/费用类别拆分预算行；审批后才允许费用报销引用。
3. 费用报销：员工提交多行费用及发票信息，必须关联已审批预算行；审批时校验可用余额，扣减预算执行额，并生成借记 6602、贷记 2241 的财务凭证。
4. 预算预警：预算执行率达到预算行阈值产生 WARNING，达到 100% 产生 OVER；同一预算行同类未关闭预警不重复创建。
5. 审批结果：审批通过为 APPROVED，驳回为 REJECTED；后续付款可以沿用现有付款/资金模块扩展为 PAID。

## 权限

- `erp:finance:budget`：成本中心、预算创建/审批
- `erp:finance:expense`：费用报销提交、审批、驳回
- `erp:finance:view`：预算和预警查询

## 关键接口

- `POST/GET /api/v1/erp/finance/cost-centers`
- `POST/GET /api/v1/erp/finance/budgets`
- `POST /api/v1/erp/finance/budgets/{id}/approve`
- `GET /api/v1/erp/finance/budget-alerts`
- `POST /api/v1/erp/finance/expenses`
- `GET /api/v1/erp/finance/expenses/{id}`
- `POST /api/v1/erp/finance/expenses/{id}/approve`
- `POST /api/v1/erp/finance/expenses/{id}/reject`
- `POST /api/v1/erp/finance/expenses/{id}/pay`

## 验收标准

- 未审批预算不能被报销引用。
- 报销审批超过预算可用余额时事务失败，预算消费额、凭证和报销状态全部回滚。
- 审批通过后预算消费额增加、凭证借贷平衡，达到阈值生成预警。
- 重复审批不会重复扣减预算或生成第二张凭证。
- 期间关账后不能新增预算或费用报销。
- MySQL 迁移、后端回滚脚本、静态插件检查和前端构建全部通过。
