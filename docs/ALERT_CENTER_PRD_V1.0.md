# 统一预警中心 PRD V1.0

## 1. 背景与目标

现有质量 SLA、生产 Andon、库存补货、销售交付和供应商交付分别产生异常，但用户需要在一个入口查看优先级、责任人、截止时间和处理入口。本功能提供跨域只读聚合，保留各业务域原始状态和处理动作，不复制业务单据。

## 2. 业务范围

| 来源 | 纳入条件 | 严重级别 | 处理入口 |
|---|---|---|---|
| 质量 | SLA 告警未关闭 | OVERDUE 为 CRITICAL，其余 HIGH | 质量 SLA 工作项 |
| Andon | 事件未解决/取消 | 沿用 LOW/MEDIUM/HIGH/CRITICAL | Andon 现场处理 |
| 库存 | 补货建议为 SHORTAGE/REORDER 且未释放 | SHORTAGE 为 HIGH，REORDER 为 MEDIUM | 补货建议 |
| 销售 | 交付绩效非 OTIF | OPEN 为 HIGH，其余为 CRITICAL | 销售交付 |
| 采购 | 供应商交付绩效非 OTIF | OPEN 为 HIGH，其余为 CRITICAL | 采购交付 |

## 3. 接口

`GET /api/v1/monitors/alerts`

查询参数：`source`、`status`、`limit(1-500)`。

统一返回 `total`、`open_count`、`overdue_count`、`by_source` 和 `items`。每条明细包含来源、类型、业务编号、严重级别、状态、截止时间、责任人、处理入口和域明细。

## 4. 验收标准

1. 五类来源可以在一个接口中查询并按来源/状态过滤。
2. 返回结果不创建或修改业务单据；原始业务域负责状态变更和审计。
3. 统一预警中心前端页面可刷新、筛选、分页，并能跳转原业务处理页。
4. 后端全量 pytest、前端 typecheck 和 production build 通过。
