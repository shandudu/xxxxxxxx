# ERP + MES 项目交付基线 V1.0

## 目标

将 `F:\pythonProject\fastapi_best_architecture` 作为唯一运行项目，形成可部署、可演示、可验收的制造业 ERP + MES 基线。业务主链路为：

`主数据 → 销售订单 → ATP/CTP → MPS/MRP → 补货/采购/生产 → 质量放行 → 发货签收 → OTIF → 客诉/RMA → NCR/CAPA/8D → 批次追溯与 KPI`

## 部署约束

- 数据库统一使用 MySQL 8，Docker Compose 服务名为 `fba_mysql`，容器端口为 `3306`。
- Redis、RabbitMQ、Celery、Nginx 与后端服务沿用现有 Compose 拓扑。
- C 盘 `C:\Users\7\Documents\python+fastapi` 不作为运行时依赖；所有后端代码、迁移、脚本和文档以 F 盘项目为准。

## 基线验收命令

在项目根目录执行：

```powershell
python scripts/validate_project_baseline.py
python scripts/validate_mes_erp_mysql.py --mysql
python scripts/validate_migration_head.py
python scripts/validate_route_permissions.py
python scripts/validate_manufacturing_happy_path_rollback.py
cd backend
pytest -q
```

完整后端验收可直接执行：

```powershell
python scripts/validate_project_acceptance.py --include-frontend
```

如果暂时没有可连接的 MySQL，可使用 `--skip-mysql`，但正式交付必须执行不跳过数据库检查的版本。

制造闭环脚本默认在一个真实 MySQL 事务中执行并回滚；需要保留演示数据时显式传入 `--commit`。销售订单驱动闭环、质量、Andon、补货、OTIF 和售后回归脚本位于 `scripts/` 目录，可按部署清单逐项执行。

前端在 `F:\pythonProject\fastapi-best-architecture-ui-master` 执行 typecheck 和 production build。

## 交付门槛

1. 业务模块必须同时具备模型/迁移、服务、API、权限依赖和前端入口。
2. 关键状态流转必须有正向演示脚本或回归测试，并验证回滚不污染数据。
3. MySQL schema、迁移升级/降级、全量 pytest、前端 typecheck/build 均通过。
4. 端到端验收覆盖订单承诺、计划供应、生产质量、交付 OTIF、售后改善和批次追溯。
