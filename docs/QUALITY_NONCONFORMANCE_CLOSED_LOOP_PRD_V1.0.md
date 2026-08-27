# 质量异常处理闭环 PRD V1.0

## 1. 业务目标

在现有 `quality` 插件的检验、NCR、MRB、库存和供应商退货能力上，补齐质量异常从发现到关闭的可执行闭环：

```text
检验 FAIL/PARTIAL
    ↓
NCR
    ↓
MRB 处置
    ├─ USE_AS_IS        → 批次放行
    ├─ REWORK           → 返工任务 → 复检 → 放行/再次异常
    ├─ REINSPECT        → 复检 → 放行/再次异常
    ├─ SCRAP            → 库存报废流水
    └─ RETURN_TO_SUPPLIER → 库存退供流水 + 供应商退货单
    ↓
NCR DISPOSED
    ↓
NCR CLOSED（记录根因）
```

本 PRD 扩展现有质量插件，不新建平行的质量中心，不复制 C 盘 SQLite 代码。

## 2. 当前代码盘点与本期差异

当前 F 项目已经存在：

- `QualityInspection`、`NonconformanceReport`、`NonconformanceDisposition`。
- `SCRAP`、`RETURN_TO_SUPPLIER`、`USE_AS_IS`、`REINSPECT` 的基础执行逻辑。
- 库存不可变流水和供应商退货单。
- NCR 创建、处置执行和关闭 API。

本期补齐：

1. `REWORK` 不再只是标记完成，而是生成可跟踪的返工任务。
2. 返工任务拥有 `PLANNED → IN_PROGRESS → AWAITING_RETEST → RELEASED` 生命周期。
3. 返工完成必须生成 RETEST；只有复检 PASS 才能放行批次。
4. `REINSPECT` 和 `REWORK` 的复检未通过时，NCR 不得进入 `DISPOSED`。
5. 报废、退供、返工、复检均保持幂等，失败事务整体回滚。
6. 退供必须找到原供应商收货行，不能生成缺少来源行的退货单。

## 3. 业务范围

### 3.1 一期包含

- 来料、过程、终检、复检产生 NCR。
- NCR 数量分配和 MRB 处置。
- 批次报废、供应商退供、按原批次返工、复检放行。
- 返工任务查询、开始、完成。
- NCR 状态和批次质量状态联动。

### 3.2 明确不做

- 不在本期实现完整 APS/设备工艺排程。
- 不将返工任务强行写入标准 Routing 或覆盖原工单快照。
- 不做跨批次自动拆分、合批和成本重算。
- 不自动物理删除 NCR、处置、返工任务或库存流水。
- 不允许控制器直接写库存余额；所有库存变化仍调用 `InventoryService.post_transaction`。

## 4. 数据模型

### 4.1 复用现有对象

- `QualityInspection`
- `NonconformanceReport`
- `NonconformanceDisposition`
- `MaterialLot`
- `StockTransaction`
- `SupplierReturn` / `SupplierReturnLine`

### 4.2 新增 `mes_quality_rework_order`

| 字段 | 说明 |
| --- | --- |
| `id` | 稳定主键 |
| `rework_no` | 返工单号，唯一 |
| `ncr_id` | 来源 NCR ID |
| `material_id` | 物料 ID |
| `lot_id` | 原批次 ID；一期返工不复制实时库存余额 |
| `quantity` | 返工数量 |
| `status` | `PLANNED/IN_PROGRESS/AWAITING_RETEST/RELEASED/CANCELLED` |
| `reinspection_id` | 返工完成后生成的 RETEST ID，可空 |
| `started_at` / `completed_at` / `released_at` | 生命周期时间 |
| `remark` | 返工说明 |

`NonconformanceDisposition.rework_order_id` 关联返工任务。返工任务只保存异常处理事实，不替代生产工单。

## 5. 状态和业务规则

### 5.1 NCR

```text
OPEN → UNDER_REVIEW → DISPOSED → CLOSED
```

- 只有完成且结果为 `FAIL/PARTIAL` 的检验可以创建 NCR。
- NCR 数量不得超过检验拒收数量。
- 已 `DISPOSED/CLOSED` 的 NCR 不得新增处置。
- 只有所有异常数量均被执行处置，且 REWORK/REINSPECT 的复检均 PASS，NCR 才能 `DISPOSED`。
- 只有 `DISPOSED` 才能关闭，并记录根因。

### 5.2 MRB

- `CREATE_DISPOSITION` 默认生成 `APPROVED`，现有权限模型将创建视为批准；后续可扩展独立审批。
- 所有处置数量之和不得超过 NCR 数量。
- `SCRAP`、`RETURN_TO_SUPPLIER` 必须提供库存仓库和库位。
- `SCRAP` 生成 `SCRAP` 负库存流水。
- `RETURN_TO_SUPPLIER` 生成 `PURCHASE_RETURN` 流水和供应商退货单，必须保留原收货单/收货行来源。
- `USE_AS_IS` 将批次质量状态设为 `PASS`。
- `REINSPECT` 生成父检验为原检验的 RETEST。
- `REWORK` 生成一张返工任务；返工完成后才生成 RETEST。

### 5.3 返工

- 返工任务创建时原批次仍保持 `HOLD`，不伪造库存转移。
- 只有 `PLANNED` 可以开始；只有 `IN_PROGRESS` 可以完成。
- 完成返工必须生成一张幂等 RETEST，并进入 `AWAITING_RETEST`。
- RETEST PASS：返工任务 `RELEASED`，批次 `PASS`，刷新 NCR 状态。
- RETEST FAIL/PARTIAL：返工任务保持 `AWAITING_RETEST`，批次保持 `HOLD`，NCR 不得关闭。

## 6. API

复用现有质量 API，并增加返工任务接口：

| 方法 | 地址 | 权限 | 作用 |
| --- | --- | --- | --- |
| GET | `/api/v1/mes/quality/rework-orders` | `mes:quality:view` | 查询返工任务 |
| POST | `/api/v1/mes/quality/rework-orders/{id}/start` | `mes:quality:mrb:execute` | 开始返工 |
| POST | `/api/v1/mes/quality/rework-orders/{id}/complete` | `mes:quality:mrb:execute` | 完成返工并生成 RETEST |
| GET | `/api/v1/mes/quality/ncrs/{id}/dispositions` | `mes:quality:view` | 查询 MRB 明细 |
| POST | `/api/v1/mes/quality/dispositions/{id}/execute` | `mes:quality:mrb:execute` | 执行报废/退供/复检/返工 |

## 7. 错误码

- `NCR_QUANTITY_EXCEEDS_REJECTED`
- `MRB_QUANTITY_EXCEEDS_NCR`
- `MRB_STOCK_POSITION_REQUIRED`
- `MRB_REWORK_LOT_REQUIRED`
- `REWORK_NOT_STARTABLE`
- `REWORK_NOT_COMPLETABLE`
- `REWORK_ALREADY_RELEASED`
- `RETEST_REQUIRED_BEFORE_NCR_DISPOSE`
- `SUPPLIER_RECEIPT_LINE_NOT_FOUND`
- `NCR_NOT_FULLY_DISPOSED`

## 8. 测试与验收

必须覆盖：

1. FAIL/PARTIAL 检验可创建 NCR，PASS 不可创建。
2. MRB 数量超出 NCR、库存位置缺失、返工无批次均被拒绝。
3. 报废和退供产生正确库存流水，退供有原收货行来源。
4. 返工任务状态转换、重复完成幂等、RETEST 创建幂等。
5. RETEST 未 PASS 时 NCR 不得 DISPOSED/CLOSED；PASS 后才能放行并关闭。
6. MySQL 事务失败回滚，不产生半套处置或库存流水。
7. 后端插件测试、MySQL 回滚验证和前端类型检查通过。

## 9. Definition of Done

- 新表模型、Schema、Service、API、插件注册可加载。
- 现有 NCR/MRB API 兼容，新增返工接口可调用。
- 报废、退供、返工、复检均可从 NCR 追溯到库存和批次。
- 文档、错误码、测试与真实代码一致。
