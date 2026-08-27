# CAPA / 8D 改善闭环 PRD V1.0

## 1. 目标

在现有 NCR、MRB、返工和复检基础上，补齐质量问题的根因分析、遏制、纠正、预防和效果验证，形成：

`NCR → CAPA/8D → 措施执行 → 效果验证 → CAPA 关闭 → NCR 关闭`

一个 NCR 最多关联一个 CAPA；没有关闭的 CAPA 时，NCR 不允许关闭。

## 2. 8D 字段

| 维度 | 内容 |
|---|---|
| D1 | 团队与责任人 |
| D2 | 问题描述、影响范围 |
| D3 | 临时遏制措施 |
| D4 | 根本原因 |
| D5 | 永久纠正方案 |
| D6 | 措施实施结果 |
| D7 | 防止再发生/体系预防 |
| D8 | 经验固化与关闭总结 |

措施分为 `CONTAINMENT`（遏制）、`CORRECTIVE`（纠正）、`PREVENTIVE`（预防），每条措施有负责人、截止日期、证据和状态。

## 3. 状态流转

### CAPA

`OPEN → ANALYSIS → ACTION → VERIFYING → CLOSED`

验证失败时回到 `ACTION`；`CANCELLED` 为终止状态。

### 措施

`OPEN → IN_PROGRESS → COMPLETED → VERIFIED`

允许从 OPEN 直接完成；未完成或取消的措施不能通过 CAPA 效果验证。

## 4. 业务规则

- NCR 关闭前，如果存在 CAPA，CAPA 必须为 `CLOSED`。
- CAPA 只能从未关闭 NCR 创建；同一 NCR 不允许重复创建 CAPA。
- CAPA PASS 验证必须填写 D4 根因，并且所有未取消措施为 `COMPLETED` 或 `VERIFIED`。
- CAPA FAIL 验证会回到 `ACTION`，保留验证历史，允许继续修改和补充措施。
- CAPA 关闭必须存在最近一次 PASS 验证，且 NCR 已经 `DISPOSED` 或 `CLOSED`。
- CAPA、措施和验证记录均使用 MySQL 事务；失败自动回滚。

## 5. API

```text
GET    /api/v1/mes/quality/capas
POST   /api/v1/mes/quality/capas
PUT    /api/v1/mes/quality/capas/{id}
GET    /api/v1/mes/quality/capas/{id}/actions
POST   /api/v1/mes/quality/capas/{id}/actions
POST   /api/v1/mes/quality/capas/{id}/actions/{action_id}/status
GET    /api/v1/mes/quality/capas/{id}/verifications
POST   /api/v1/mes/quality/capas/{id}/verify
POST   /api/v1/mes/quality/capas/{id}/close
```

## 6. 验收标准

- 可从 NCR 创建唯一 CAPA，填写完整 8D 内容。
- 可新增遏制、纠正、预防措施并推进状态、记录证据。
- 未填写根因或措施未完成时，PASS 验证被拒绝。
- FAIL 验证后 CAPA 回到 ACTION，可追加整改；PASS 后进入 VERIFYING。
- CAPA 关闭后，NCR 才能关闭；重复操作具备幂等或明确业务冲突。
- MySQL Alembic 升级成功，真实事务回滚验证通过，现有质量和全插件测试不回归。
