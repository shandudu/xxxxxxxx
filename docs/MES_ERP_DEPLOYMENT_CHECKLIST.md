# MES + ERP 部署与验收清单

## 后端

项目级后端验收（推荐上线前执行）：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_project_acceptance.py
```

该命令按顺序执行项目基线、权限扫描、MySQL schema、制造/销售/采购/库存/生产/质量/售后回滚验收。
追加 `--include-frontend` 会继续执行前端 typecheck 和 production build。

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe -m pytest backend\tests\plugin -q
.\.venv\Scripts\fba.exe run --host 127.0.0.1 --port 8000 --no-reload --workers 1
```

文档地址以当前项目配置为准：`http://127.0.0.1:8000/docs`，OpenAPI 为 `http://127.0.0.1:8000/openapi`。

如果 8000 端口被占用，可先用以下命令确认监听进程，再选择 8001：

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8000,8001
.\.venv\Scripts\fba.exe run --host 127.0.0.1 --port 8001 --no-reload --workers 1
```

## 前端

```powershell
cd F:\pythonProject\fastapi-best-architecture-ui-master
pnpm --filter @vben/web-antdv-next typecheck
pnpm --filter @vben/web-antdv-next build
pnpm --filter @vben/web-antdv-next dev
```

## 菜单和权限

新增根菜单：`MesInventory`、`ErpPurchasing`、`MesOperationMaterial`、`MesProduction`、`MesQuality`、`ErpSales`。质量模块新增 `mes:quality:config` 按钮权限。超级管理员自动拥有全部菜单；普通角色需在系统角色管理中显式勾选根菜单及按钮权限。

## 数据库

本次安装采用插件标准机制：模型元数据只创建缺失表，插件 SQL 写菜单和种子数据。禁止使用全库初始化命令重建已有生产数据库。

上线前建议先备份数据库，并在预发布环境执行一次采购收货、工序物料计划生效、工单工序执行与实际耗料、生产领退料、报工、逐项质量检验、NCR 报废/退供和销售发货的完整业务数据验收。

## C → F 业务规则差异与 MySQL 验证

F 以插件模型为唯一业务数据来源，不执行 C 项目的 SQLite Alembic 迁移，也不复制 C 的认证表。供应商收货在存在生效来料检验模板时，会在同一事务中自动创建 IQC 检验记录并将批次置为质量 HOLD；生产报工生成成品批次时，如果存在生效终检模板，也会在同一事务中创建终检记录并将批次置为质量 HOLD；没有模板时保持原有兼容行为。

执行只读基线检查：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_mes_erp_mysql.py
.\.venv\Scripts\python.exe scripts\validate_mes_erp_mysql.py --mysql
```

检查内容包括 18 个业务插件的模型/API/Service/Schema/SQL 文件、`mes_`/`erp_` 表命名、MySQL 连接、核心业务表以及库存幂等与追踪序列字段。该脚本不会创建表、执行迁移或写入业务数据。

## 质量异常闭环

设计规则见 [QUALITY_NONCONFORMANCE_CLOSED_LOOP_PRD_V1.0.md](QUALITY_NONCONFORMANCE_CLOSED_LOOP_PRD_V1.0.md) 和 [QUALITY_REWORK_PRODUCTION_RELEASE_PRD_V1.0.md](QUALITY_REWORK_PRODUCTION_RELEASE_PRD_V1.0.md)。本期新增返工任务表、MRB 关联字段以及返工任务到生产工单的外键，已有数据库必须先执行：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\fba.exe alembic upgrade
```

质量异常真实事务回滚验证（默认不保留测试数据）：

```powershell
.\.venv\Scripts\python.exe scripts\validate_quality_nonconformance_rollback.py
```

返工 API：

```text
GET  /api/v1/mes/quality/rework-orders
POST /api/v1/mes/quality/rework-orders/{id}/create-work-order
POST /api/v1/mes/quality/rework-orders/{id}/start
POST /api/v1/mes/quality/rework-orders/{id}/complete
```

返工完成接口要求关联生产工单已 `COMPLETED` 且完工数量不低于返工数量；否则不会创建 RETEST。返工生产工单完整明细通过生产模块的 work-order API 查询。

## CAPA / 8D 改善闭环

设计规则见 [QUALITY_CAPA_8D_PRD_V1.0.md](QUALITY_CAPA_8D_PRD_V1.0.md)。CAPA 迁移随 Alembic head 执行，真实 MySQL 回滚验证：

```powershell
.\.venv\Scripts\python.exe scripts\validate_quality_capa_rollback.py
```

CAPA 关闭前必须完成 D4 根因、至少一条整改措施和 PASS 效果验证；存在 CAPA 时，NCR 也必须等 CAPA 关闭后才允许关闭。

## 客户投诉与 RMA 闭环

设计与验收规则见 [CUSTOMER_RMA_NCR_CAPA_PRD_V1.0.md](CUSTOMER_RMA_NCR_CAPA_PRD_V1.0.md)。MySQL 回滚验证：

```powershell
.\.venv\Scripts\python.exe scripts\validate_customer_rma_rollback.py
```

预期输出 `CUSTOMER_RMA_RUN_OK status=CLOSED` 和 `CUSTOMER_RMA_ROLLBACK_OK`。RMA 接收会生成 `CUSTOMER_RETURN` 库存流水并将批次置为 HOLD；退货检验不合格会自动生成 NCR，NCR/CAPA 关闭后才能登记客户处理结果。

售后处理执行验证：

```powershell
.\.venv\Scripts\python.exe scripts\validate_customer_after_sales_rollback.py
```

预期输出 `CUSTOMER_AFTER_SALES_RUN_OK types=REFUND,REPLACEMENT,REPAIR,SCRAP` 和 `CUSTOMER_AFTER_SALES_ROLLBACK_OK`。换货、报废会写入幂等库存流水，维修必须先完成维修任务。

质量与售后运营驾驶舱验证：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_quality_operation_dashboard_rollback.py
```

预期输出 `QUALITY_OPERATION_DASHBOARD_RUN_OK` 和 `QUALITY_OPERATION_DASHBOARD_ROLLBACK_OK`，并确认 SLA 告警可确认、升级、关闭。

生产 Andon 异常派工闭环验证：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_production_andon_rollback.py
```

预期输出 `PRODUCTION_ANDON_RUN_OK` 和 `PRODUCTION_ANDON_ROLLBACK_OK`，并确认停机/缺料/质量异常可以派工、开始、升级、恢复关闭。

订单 ATP/CTP 交期评估验证：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_sales_order_promise_rollback.py
```

预期输出 `SALES_PROMISE_RUN_OK` 和 `SALES_PROMISE_ROLLBACK_OK`，确认库存、采购和在制生产供给会生成订单行级交期风险快照。

销售交付与 OTIF 规则见 [SALES_ORDER_DELIVERY_OTIF_PRD_V1.0.md](SALES_ORDER_DELIVERY_OTIF_PRD_V1.0.md)，可执行交付回归：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_sales_delivery_otif_rollback.py
```

预期输出 `SALES_DELIVERY_OTIF_RUN_OK` 和 `SALES_DELIVERY_OTIF_ROLLBACK_OK`。

供应商采购 OTIF 与缺料影响规则见 [SUPPLIER_PURCHASE_OTIF_IMPACT_PRD_V1.0.md](SUPPLIER_PURCHASE_OTIF_IMPACT_PRD_V1.0.md)，可执行采购回归：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_supplier_purchase_otif_rollback.py
```

预期输出 `SUPPLIER_PURCHASE_OTIF_RUN_OK` 和 `SUPPLIER_PURCHASE_OTIF_ROLLBACK_OK`。

安全库存与自动补货规则见 [INVENTORY_SAFETY_REPLENISHMENT_PRD_V1.0.md](INVENTORY_SAFETY_REPLENISHMENT_PRD_V1.0.md)，可执行补货回归：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_inventory_replenishment_rollback.py
```

预期输出 `INVENTORY_REPLENISHMENT_RUN_OK` 和 `INVENTORY_REPLENISHMENT_ROLLBACK_OK`。

MRP 净需求与 ATP/CTP 自动重算规则见 [MRP_NET_REQUIREMENT_ACTION_PRD_V1.0.md](MRP_NET_REQUIREMENT_ACTION_PRD_V1.0.md)。MRP 运算完成、计划订单释放后会自动刷新确认中和部分发货销售订单的承诺快照，也可调用 `POST /api/v1/erp/sales/promise/recalculate` 手工触发。

## 销售订单驱动 Happy Path

设计与验收规则见 [SALES_ORDER_DRIVEN_HAPPY_PATH_PRD_V1.0.md](SALES_ORDER_DRIVEN_HAPPY_PATH_PRD_V1.0.md)。演示入口复用 `demo` 插件，调用顺序为：

```text
销售订单确认 → MPS/MRP → 采购/生产计划订单释放 → 收货/领料/报工
→ 质检放行 → 发货 → 正向/反向追溯
```

API：

```text
POST /api/v1/mes/demo/sales-order-driven-happy-path/run
GET  /api/v1/mes/demo/sales-order-driven-happy-path/status
POST /api/v1/mes/demo/sales-order-driven-happy-path/verify
```

在预发布 MySQL 中进行真实事务验证（默认执行后回滚，不保留演示数据）：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_sales_order_driven_happy_path.py
```

制造闭环（供应商收货 → 领料 → 工序执行 → 成品检验 → 销售发货 → 追溯）可执行：

```powershell
cd F:\pythonProject\fastapi_best_architecture
.\.venv\Scripts\python.exe scripts\validate_manufacturing_happy_path_rollback.py
```

预期输出 `MANUFACTURING_HAPPY_PATH_RUN_OK passed=True` 和
`MANUFACTURING_HAPPY_PATH_ROLLBACK_OK`。
