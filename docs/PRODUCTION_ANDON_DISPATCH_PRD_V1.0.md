# 生产异常 Andon + 派工闭环 PRD V1.0

## 1. 目标

把现场停机、缺料和质量异常统一成可响应、可派工、可升级、可恢复的 Andon 事件，关联生产工单、工序、设备、物料和 NCR，形成从现场发现到恢复验证的闭环。

## 2. 事件类型与状态

- 类型：STOPPAGE（停机）、MATERIAL_SHORTAGE（缺料）、QUALITY（质量异常）。
- 状态：OPEN → ACKNOWLEDGED → IN_PROGRESS → RESOLVED；无法继续时进入 BLOCKED，可 CANCELLED。
- 每次创建自动生成事件号、责任 SLA 截止时间和操作审计；重复派工保留历史记录。

## 3. SLA 与升级

默认 SLA：停机 2 小时、缺料 4 小时、质量异常 8 小时。超时进入驾驶舱超期统计；升级动作递增升级级别并写入不可变动作记录。责任人确认后必须开始处理，关闭时记录根因、处理说明和恢复时间。

## 4. API

- `GET /api/v1/mes/production/andon/dashboard`
- `GET/POST /api/v1/mes/production/andon/events`
- `POST /andon/events/{id}/assign|start|resolve|escalate|cancel`
- `GET /andon/events/{id}/assignments|actions`

查询使用 `mes:production:view`，创建和状态变更使用 `mes:production:execute`。

## 5. 页面与验收

生产页面增加 Andon 看板，展示活动数、超期数、类型/优先级/状态分布和平均恢复时长；左侧事件列表支持按状态和类型筛选，右侧显示关联对象、SLA、派工和动作历史，并提供确认、开始、升级、恢复和取消操作。

验收：MySQL 迁移可升级/回滚，事件状态和派工审计完整，统计与明细一致，异常闭环验证脚本通过，后端全量测试及前端 typecheck/build 通过。
