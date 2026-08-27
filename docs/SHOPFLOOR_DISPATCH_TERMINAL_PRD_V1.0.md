# 车间派工、班组与工位终端模块 PRD V1.0

## 1. 业务目标

在现有 APS 排程、工序派工和生产执行能力之间补齐车间现场层，使系统能够回答：

1. 哪个班组和人员负责某个工作中心；
2. 具体在哪个工位执行；
3. 操作员当前登录了哪个工位；
4. 已接收的派工如何转成真实生产执行记录；
5. 派工、工序快照与生产实绩之间如何追溯。

本期形成以下闭环：

```text
APS 已发布工序
→ 派工到班组 / 人员 / 工位
→ 操作员登录工位终端
→ 接收并开工
→ ProductionExecution
→ 完工
→ 派工与排程工序状态同步
```

## 2. 现有能力与冲突检查

### 2.1 复用能力

- `mes_aps_dispatch` 已支持派工数量、人员、班组文本、工位编码文本和状态；
- `mes_aps_operation_schedule` 已保存工作中心、工单工序和计划时间；
- `ProductionExecutionService` 已支持工序开工、物料消耗和完工；
- `sys_user` 作为操作员身份来源；
- `mes_work_center` 表示资源组，`mes_equipment` 表示实际设备；
- 权限、统一响应、异常、事务和菜单体系全部复用。

### 2.2 本期修正

现有 `assigned_team` 与 `workstation_code` 只是文本快照，不能支撑稳定关联。本期新增：

- `team_id`：班组稳定 ID；
- `workstation_id`：工位稳定 ID；
- `production_execution_id`：派工对应的生产执行 ID；

原文本字段继续保留为历史快照，不删除、不覆盖历史。

## 3. 范围

### 3.1 本期实现

- 生产班组主数据；
- 班组成员及角色；
- 工位主数据；
- 工位与工作中心、可选设备关联；
- 操作员工位签到、签退；
- 工位终端待办派工；
- 派工接收、开工和完工；
- 派工与 `ProductionExecution` 关联；
- MES 菜单、权限、API、前端页面和测试。

### 3.2 本期不做

- 考勤、薪资和完整 HR；
- 技能矩阵和上岗证；
- 多人协同工时分摊；
- PLC/SCADA 自动报工；
- PDA 原生应用；
- 复杂安灯、电子作业指导书和参数采集。

## 4. 核心对象

| 对象 | 表 | 说明 |
|---|---|---|
| ProductionTeam | `mes_production_team` | 生产班组主数据 |
| ProductionTeamMember | `mes_production_team_member` | 班组与系统用户关系 |
| Workstation | `mes_workstation` | 工作中心下的现场工位 |
| WorkstationSession | `mes_workstation_session` | 操作员工位登录事实 |
| ApsDispatch 扩展 | `mes_aps_dispatch` | 新增班组、工位和执行 ID |

## 5. 数据模型

### 5.1 ProductionTeam

- `team_code`：唯一业务编码；
- `team_name`；
- `work_center_id`：可空，空表示可跨工作中心；
- `leader_user_id`：可空；
- `status`：`ACTIVE / DISABLED`；
- `remark`、审计字段。

### 5.2 ProductionTeamMember

- `team_id`；
- `user_id`；
- `member_role`：`LEADER / OPERATOR / QUALITY / MATERIAL / OTHER`；
- `status`：`ACTIVE / DISABLED`；
- 同一班组、同一用户仅允许一条有效记录。

### 5.3 Workstation

- `workstation_code`：唯一业务编码；
- `workstation_name`；
- `work_center_id`：必填；
- `equipment_id`：可空；
- `terminal_enabled`；
- `status`：`ACTIVE / DISABLED`；
- `remark`、审计字段。

Routing 仍只绑定 WorkCenter，工位和设备只在现场执行层使用。

### 5.4 WorkstationSession

- `workstation_id`；
- `user_id`；
- `team_id`：可空；
- `status`：`ACTIVE / CLOSED`；
- `signed_in_at`、`signed_out_at`、`last_activity_at`；
- 同一用户同时只能存在一个活动工位会话。

### 5.5 ApsDispatch 增量字段

- `team_id`；
- `workstation_id`；
- `production_execution_id`；
- 原 `assigned_team`、`workstation_code` 保存派工时快照。

## 6. 状态和业务规则

### 6.1 班组与工位

- 禁用班组不能新增成员或接受新派工；
- 禁用工位不能签到和开工；
- 工位的设备必须启用且允许生产；
- 工位工作中心必须与派工工作中心一致。

### 6.2 签到

- 操作员只能保留一个活动工位会话；
- 重复登录同一工位幂等返回当前会话；
- 切换工位前必须签退；
- 指定班组时，当前用户必须是该班组有效成员。

### 6.3 派工

- 派工仍由 APS 服务创建；
- 新派工可按 `assigned_user_id / team_id / workstation_id` 任一维度指派；
- 班组、工位写入稳定 ID，同时保存名称/编码快照；
- 派工工位必须属于派工工作中心；
- 班组限定工作中心时必须与派工工作中心一致。

### 6.4 开工与完工

- `DISPATCHED` 可在终端自动接收后开工，`ACCEPTED` 可直接开工；
- 开工调用既有 `ProductionExecutionService.start`；
- 每张派工只允许关联一个生产执行；
- 完工调用既有 `ProductionExecutionService.complete`；
- 完工数量不得超过派工数量；
- 派工完成后状态为 `COMPLETED`；
- 同一排程工序下所有有效派工完成后，排程工序更新为 `COMPLETED`。

## 7. API

基础前缀：`/api/v1/mes/shopfloor`

### 7.1 班组

- `GET /teams`
- `POST /teams`
- `PUT /teams/{id}`
- `PUT /teams/{id}/status`
- `POST /teams/{id}/members`
- `PUT /teams/{id}/members/{member_id}/status`
- `GET /users/options`

### 7.2 工位

- `GET /workstations`
- `POST /workstations`
- `PUT /workstations/{id}`
- `PUT /workstations/{id}/status`
- `GET /workstations/options`

### 7.3 终端

- `GET /terminal/{workstation_id}/context`
- `POST /terminal/{workstation_id}/check-in`
- `POST /terminal/sessions/{session_id}/check-out`
- `POST /terminal/dispatches/{dispatch_id}/start`
- `POST /terminal/dispatches/{dispatch_id}/complete`

## 8. 页面

MES 制造管理下新增“车间终端”菜单，页面包含：

1. 班组管理：班组、负责人、成员；
2. 工位管理：工作中心、设备、终端状态；
3. 工位终端：签到状态、待办派工、接收、开工、完工。

## 9. 权限

- `mes:shopfloor:view`
- `mes:shopfloor:team`
- `mes:shopfloor:workstation`
- `mes:shopfloor:operate`

## 10. 错误码

- `PRODUCTION_TEAM_NOT_FOUND`
- `PRODUCTION_TEAM_DISABLED`
- `TEAM_MEMBER_NOT_FOUND`
- `TEAM_MEMBER_EXISTS`
- `WORKSTATION_NOT_FOUND`
- `WORKSTATION_DISABLED`
- `WORKSTATION_CENTER_MISMATCH`
- `WORKSTATION_EQUIPMENT_INVALID`
- `OPERATOR_NOT_TEAM_MEMBER`
- `OPERATOR_ALREADY_CHECKED_IN`
- `WORKSTATION_SESSION_NOT_FOUND`
- `DISPATCH_NOT_STARTABLE`
- `DISPATCH_EXECUTION_ALREADY_EXISTS`
- `DISPATCH_COMPLETION_QUANTITY_INVALID`

## 11. 事务、历史与并发

- 派工开工、执行创建和状态同步在一个事务中完成；
- 派工完工、执行完工和排程状态同步在一个事务中完成；
- 签到时锁定当前用户活动会话查询，防止重复签到；
- 班组名和工位编码快照保护历史，主数据更名不改变旧派工展示；
- 不物理删除班组、成员、工位和终端会话。

## 12. Definition of Done

- 增量 Migration 完成且可升级；
- 模型、Schema、Service、API 完成；
- APS 派工支持稳定班组和工位 ID；
- 工位签到、派工开工和完工闭环可运行；
- 前端班组、工位、终端页面可使用；
- 菜单和权限完成；
- 后端测试、前端类型检查和构建通过；
- 使用真实数据库事务完成核心路径验证。
