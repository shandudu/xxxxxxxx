# DEMO 业务数据包 PRD V1.0

## 1. 目的

为 MES/ERP 前后端页面提供一套可以直接浏览和演示的关联业务数据，避免首次使用时需要逐张单据手工创建。数据覆盖制造闭环与销售订单驱动闭环，所有关键记录都能从上游单据追溯到下游结果。

## 2. 数据范围

| 业务域 | 已提供数据 | 业务结果 |
| --- | --- | --- |
| 基础资料 | 单位、物料分类、原材料、成品、供应商、客户、仓库/库区/库位 | 主数据可用于采购、生产和销售 |
| 工艺资料 | 工序、工作中心、BOM、工艺路线 | 成品可生成工单并计算用料 |
| 采购与库存 | 采购订单、收货、原材料 Lot、库存结存和流水 | 原材料已完成收货入库 |
| 计划与生产 | 销售订单、MPS/MRP、计划订单、工单、领料、工序执行、完工报工 | 成品已完工并生成 Lot |
| 质量与追溯 | 来料/终检合格记录、原材料到成品的 Lot 追溯关系 | 成品质量放行且可正向/反向追溯 |
| 销售交付 | 销售订单、发货单、发货库存流水 | 成品已按订单完成发货 |

## 3. 场景与编码

### 制造闭环

`MANUFACTURING_HAPPY_PATH` 使用 `DEMO-*` 编码，主业务链为：

`DEMO-PO-001` → `DEMO-RCV-001` → `DEMO-RM-LOT-001` → `DEMO-WO-001` → `DEMO-ISS-001` → `DEMO-EXE-001` → `DEMO-RPT-001` → `DEMO-FG-LOT-001` → `DEMO-QI-001` → `DEMO-SO-001` → `DEMO-SHP-001`。

### 销售订单驱动闭环

`SALES_ORDER_DRIVEN_HAPPY_PATH` 使用 `DEMO-SOD-*` 编码，主业务链为：

销售订单 → `DEMO-SOD-MPS-001` → MRP 建议 → 采购收货 `DEMO-SOD-RCV-001` → 原材料 Lot `DEMO-SOD-RM-LOT-001` → 工单/领料/执行 → `DEMO-SOD-RPT-001` → 成品 Lot `DEMO-SOD-FG-LOT-001` → 终检 → `DEMO-SOD-SHP-001`。

## 4. 导入与重复执行

推荐在本地开发库通过服务层生成数据：

```powershell
.\.venv\Scripts\python.exe scripts\validate_manufacturing_happy_path_rollback.py --commit
.\.venv\Scripts\python.exe scripts\validate_sales_order_driven_happy_path.py --commit
```

上述命令可重复执行，场景按稳定业务编码识别，已存在的单据不会重复新增。

完整数据库快照在 [seed_business_demo_data.sql](/F:/pythonProject/fastapi_best_architecture/backend/plugin/demo/sql/mysql/seed_business_demo_data.sql)。该 SQL 保存的是已验证数据的原始 ID 关系，只允许导入干净的开发/演示 MySQL 数据库；不能用于生产或已有业务数据的库。

## 5. 验收口径

- 两个场景在 `mes_demo_run` 中均为 `COMPLETED`。
- 采购收货、库存 Lot、工单、完工报告、质检、销售订单、发货和追溯关系均存在。
- 终检结果为 `PASS`，发货单状态为 `POSTED`。
- 可以以任一 `DEMO-*` 单号在对应菜单查询，并通过 Lot 追溯查看原料与成品的关联。
