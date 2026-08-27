# 返工任务 → 生产工单 → 复检放行 PRD V1.0

## 1. 背景与目标

当前质量闭环已经支持 NCR、MRB、返工任务和 RETEST，但返工任务完成后即可直接创建复检，缺少实际生产执行凭证。V1.0 将返工执行绑定到 MES 生产工单，形成可审计的：

`NCR/MRB(REWORK) → 返工任务 → 返工生产工单 → 报工完工 → RETEST → 放行/再次返工`

目标：

- 每个返工任务必须有对应生产工单，生产工单号可追溯回返工任务和 NCR。
- 只有生产工单实际完成且完工数量满足返工数量，才允许创建 RETEST。
- RETEST PASS 才能将返工任务置为 RELEASED，并由现有质量逻辑放行批次和 NCR。
- RETEST FAIL 保留 NCR 在审查态，允许生成下一轮返工工单，不产生重复放行。
- 全流程复用现有 MySQL、库存、批次、生产工单和质量模型，不引入 PostgreSQL 或 C 盘项目代码。

## 2. 范围

### 2.1 本版本包含

1. 返工任务与 `mes_work_order` 建立可空外键关联。
2. 根据返工物料自动选择有效 BOM/工艺路线，创建返工生产工单。
3. 返工工单自动发布；开始返工时自动开工。
4. 返工完工必须通过生产报工完成，系统校验生产工单状态和数量。
5. 完工后创建唯一 RETEST；复检 PASS/FAIL 驱动释放或再次返工。
6. 查询接口返回关联生产工单 ID，保留现有生产工单查询接口查看完整明细。
7. MySQL Alembic 迁移、回滚验证脚本和插件测试。

### 2.2 本版本不包含

- 自动排程、设备采集、工艺参数采集和返工专用 BOM/工艺路线版本管理。
- 返工物料自动领料/退料；仍使用现有生产领料、退料接口。
- 前端返工工作台；本版本先保证后端业务闭环，前端可按接口直接接入。

## 3. 角色与权限

| 角色 | 能力 |
|---|---|
| 质量工程师 | 创建/执行 MRB，查看返工任务，完成 RETEST，关闭 NCR |
| 生产计划员 | 创建返工生产工单、查看生产工单 |
| 生产操作员 | 开始返工、领料、报工 |
| 质量主管 | RETEST 判定和最终放行 |

沿用现有权限：`mes:quality:view`、`mes:quality:mrb:execute`、`mes:quality:inspection`、`mes:production:view`、`mes:production:release`、`mes:production:execute`、`mes:production:report`。

## 4. 状态与业务规则

### 4.1 返工任务状态

`PLANNED → IN_PROGRESS → AWAITING_RETEST → RELEASED`

RETTEST FAIL 时：

`AWAITING_RETEST → IN_PROGRESS`，创建新一轮返工生产工单；历史工单和历史复检保留。

### 4.2 核心门禁

- 创建生产工单：返工任务必须为 `PLANNED`，或上一轮 RETEST 为 FAIL 的 `AWAITING_RETEST`；物料必须可生产，并存在 ACTIVE BOM 与 ACTIVE Routing。
- 创建动作幂等：同一轮返工已有未完成工单时重复调用返回原工单，不重复建单。
- 开始返工：必须已关联工单；工单为 DRAFT 时先发布，再置为 `IN_PROGRESS`。
- 完成返工：关联工单必须为 `COMPLETED`，且 `completed_quantity >= rework.quantity`；否则返回业务冲突。
- 创建 RETEST：每一轮只能创建一张，重复调用返回原复检；复检样本量等于返工数量。
- RETEST PASS：返工任务为 `RELEASED`，批次质量状态为 PASS，NCR 按现有规则转 `DISPOSED`，之后才可关闭。
- RETEST FAIL：返工任务回到 `AWAITING_RETEST`，批次保持 HOLD，NCR 不得关闭。
- 任意库存、生产报工、复检写入都在同一个事务中，异常自动回滚。

## 5. API

### 5.1 创建/获取返工生产工单

`POST /api/v1/mes/quality/rework-orders/{rework_id}/create-work-order`

重复请求幂等。返回返工任务详情，其中包含 `production_work_order_id`；生产工单完整明细通过 `GET /api/v1/mes/production/work-orders/{id}` 查询。

### 5.2 开始返工

`POST /api/v1/mes/quality/rework-orders/{rework_id}/start`

自动发布 DRAFT 工单并开工；若已是进行中则幂等返回。

### 5.3 完成返工并生成复检

`POST /api/v1/mes/quality/rework-orders/{rework_id}/complete`

仅校验并消费已完成的生产工单，成功后生成 RETEST，返工任务进入 `AWAITING_RETEST`。

### 5.4 复检

沿用：

- `POST /api/v1/mes/quality/inspections/{inspection_id}/complete`
- `GET /api/v1/mes/quality/rework-orders`

复检结果由现有 `QualityService.complete_inspection` 驱动 RELEASED 或再次返工。

## 6. 验收标准

- 正常链路可完成：MRB REWORK → 创建返工工单 → 开工 → 报工 → 完工 → RETEST PASS → NCR 关闭。
- 未建工单、工单未完工、完工数量不足时，完成返工均被拒绝且数据库无脏数据。
- RETEST FAIL 后可创建下一轮工单，历史工单/复检不被覆盖。
- 重复创建工单、重复完成返工、重复完成复检均幂等。
- MySQL 迁移到最新 head 成功；回滚验证默认不残留演示数据。
- 现有插件测试、质量回归和编译检查全部通过。
