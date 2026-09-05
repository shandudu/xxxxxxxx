# 完工品扫码包装、装箱与标签追溯 PRD V1.0

## 1. 背景与目标

现有系统已支持生产工单、工序执行、完工报工、批次/SN、质量检验、库存入库和销售发货，但“包装”目前只是一种工序/工作中心类型，没有独立的包装业务对象和扫码闭环。

本期建立：

```text
完工报工 / 质量放行
→ 创建包装任务
→ 扫描工单、批次或 SN
→ 校验包装规则与质量状态
→ 扫描包装物料
→ 装入箱码
→ 封箱、称重、打印标签
→ 多箱组托
→ 包装放行
→ 成品入库 / 销售拣配发货
```

目标如下：

1. 每个销售包装单元、外箱和托盘都有唯一可追溯编码；
2. 扫描时阻止错料、错批次、重复装箱、超装、质量未放行和过期批次；
3. 包装层级能追溯到工单、成品 Lot/SN、原材料 Lot 和销售订单；
4. 包装数量与完工、库存、发货数量守恒；
5. 支持 PC、PDA 和扫码枪连续操作，弱网时不允许产生无法确认的封箱结果。

## 2. 现有能力与缺口

### 2.1 可复用能力

- `mes_work_order`、`mes_production_report`：完工来源与可包装数量；
- `mes_material_lot`、`mes_material_serial`：批次与序列号追溯；
- `mes_quality_inspection`：来料、过程和终检结论；
- `mes_inventory_balance`、`mes_stock_transaction`：库存结存及不可篡改流水；
- `mes_trace_relation`：批次/SN 上下游关系；
- `erp_sales_order`、`erp_shipment`：销售需求与发货；
- `mes_operation`、`mes_work_center`：已有 `PACKAGING` 类型；
- 现有权限、事务、审计、业务字典和中英文提示机制。

### 2.2 当前缺口

- 没有包装规格、包装 BOM 和客户包装要求；
- 没有包装任务及待包装数量；
- 没有单品码、箱码、托码的层级关系；
- 没有扫码装箱、移箱、拆箱、补箱、封箱和组托；
- 没有重量校验、标签打印记录和补打审批；
- 发货不能校验包装状态，也不能按箱/托直接扫描出库；
- 召回只能追踪 Lot，无法直接定位受影响箱码、托码和客户。

## 3. 业务范围

### 3.1 本期包含

- 包装规格和客户包装要求；
- 完工品包装任务；
- Lot 管理产品按数量装箱；
- SN 管理产品逐件扫码装箱；
- 包装材料扫描与用量记录；
- 箱码生成、扫码装箱、拆箱、移箱、封箱；
- 毛重/净重/皮重及允许偏差校验；
- 标签模板选择、打印、补打与打印历史；
- 外箱组托、拆托、托盘封托；
- 包装质量确认和放行；
- 包装完成后成品入库，以及发货按箱码/托码扫描；
- 包装层级追溯、召回影响展开、审计日志；
- PC/PDA 响应式包装工作台。

### 3.2 本期不包含

- 自动包装机、称重仪、打印机的 PLC/串口驱动；本期提供标准设备适配接口；
- 物流承运商面单和电子运单；
- 仓储波次、自动立库和输送线控制；
- 自研条码识别 SDK；扫码枪按键盘输入处理，摄像头扫码可后续接入；
- 包装设计图、3D 装箱优化和危险品合规计算。

## 4. 角色与职责

| 角色 | 主要权限 |
| --- | --- |
| 包装计划员 | 维护包装规则、创建/取消包装任务、指定销售订单 |
| 包装操作员 | 领用任务、开工、扫码装箱、拆箱/移箱、称重、封箱、组托 |
| 包装质检员 | 抽检、异常判定、包装放行/驳回 |
| 班组长 | 强制关箱、差异处理、标签补打审批 |
| 仓库人员 | 扫箱/扫托入库、拣配和发货 |
| 质量人员 | 查看隔离、NCR、召回箱码和客户影响 |

## 5. 核心业务对象

| 对象 | 建议表名 | 说明 |
| --- | --- | --- |
| PackagingSpecification | `mes_packaging_specification` | 物料/客户/销售订单适用的包装规格 |
| PackagingSpecLevel | `mes_packaging_spec_level` | 单品、内箱、外箱、托盘各级容量与标签规则 |
| PackagingMaterialRule | `mes_packaging_material_rule` | 包装箱、袋、托盘、标签等物料用量 |
| PackagingTask | `mes_packaging_task` | 包装执行任务头 |
| PackagingTaskSource | `mes_packaging_task_source` | 关联完工报告、工单、Lot 和销售订单行 |
| HandlingUnit | `mes_handling_unit` | 单品包装、箱、托盘等物流单元，简称 HU |
| HandlingUnitContent | `mes_handling_unit_content` | HU 内 Lot/SN/数量明细 |
| HandlingUnitRelation | `mes_handling_unit_relation` | 箱入托、内箱入外箱等父子层级 |
| PackagingMaterialConsumption | `mes_packaging_material_consumption` | 包装材料扫码与实际消耗 |
| PackagingWeightRecord | `mes_packaging_weight_record` | 称重值、设备来源和校验结果 |
| PackagingLabelPrint | `mes_packaging_label_print` | 标签打印、补打、作废记录 |
| PackagingInspection | `mes_packaging_inspection` | 包装外观、数量、标签和重量检查 |
| PackagingOperationLog | `mes_packaging_operation_log` | 全部扫码及状态操作的审计事实 |

## 6. 包装主数据

### 6.1 包装规格

- `spec_code`、`spec_name`、版本、状态；
- `material_id` 必填；`customer_id`、`sales_order_id` 可选；
- 优先级：销售订单专用 > 客户专用 > 物料默认；
- `effective_from/effective_to` 控制生效期；
- `lot_mixing_allowed`：同箱是否允许混 Lot；
- `production_order_mixing_allowed`：同箱是否允许混工单；
- `partial_package_allowed`：尾箱是否允许不足标准装量；
- `quality_release_required`：包装前是否必须质量放行；
- `weight_check_required`：是否必须称重通过才能封箱。

### 6.2 包装层级

每个规格至少有一个 `CARTON` 层级，可选 `EACH / INNER / CARTON / PALLET`：

- `level_no`：从内到外递增；
- `unit_quantity`：本层包含的下一级数量；
- `gross_weight_target`、`weight_tolerance_upper/lower`；
- `barcode_rule_id`、`label_template_code`；
- `container_material_id`：包装材料；
- `seal_required`、`inspection_required`。

包装规格已被任务引用后不得直接修改，必须复制新版本。

## 7. 编码与标签规则

### 7.1 编码对象

- `EACH`：单品码，可直接复用产品 SN；
- `INNER`：内包装码；
- `CARTON`：外箱码；
- `PALLET`：托盘码。

### 7.2 编码规则

- 所有 HU 编码全局唯一，建议格式：`HU-{TYPE}-{YYYYMMDD}-{SEQUENCE}`；
- 支持企业内部码和 GS1 扩展，外部条码原文同时保存；
- 扫码输入标准化后再判重，禁止仅以大小写或分隔符差异形成重复码；
- 已作废编码永不重新使用；
- 标签至少包含：物料编码/名称、规格型号、Lot、数量、单位、生产日期、有效期、箱码、工单号；客户专用字段按模板扩展。

## 8. 状态机

### 8.1 包装任务

```text
DRAFT → RELEASED → IN_PROGRESS → PACKED → INSPECTING → RELEASED_TO_STOCK → CLOSED
                     ↓             ↓           ↓
                   SUSPENDED     REJECTED    REJECTED
DRAFT / RELEASED / SUSPENDED → CANCELLED
```

### 8.2 Handling Unit

```text
OPEN → SEALED → QUALITY_HOLD → RELEASED → STORED → ALLOCATED → SHIPPED
  ↓       ↓
VOIDED  REOPENED → OPEN
```

- `OPEN` 才能增减内容或调整父子关系；
- `SEALED` 后内容和数量冻结；
- 质量不合格进入 `QUALITY_HOLD`；
- 已出库/发货 HU 不能拆箱、移箱或作废。

## 9. 核心流程与规则

### 9.1 创建包装任务

- 来源为已完成的生产报告或已完工工单；
- 自动匹配有效包装规格并保存版本快照；
- 可指定销售订单行，从而选用客户专用包装规则；
- 可包装数量 = 合格完工数量 − 已包装数量 − 已报废/隔离数量；
- 同一来源允许拆成多个包装任务，但累计数量不能超过可包装数量；
- 创建接口使用业务幂等键，重试不得重复占用数量。

### 9.2 开工与扫描来源

操作员扫描任务码、工单号、生产报告号、Lot 或 SN 进入任务：

- 物料必须与任务一致；
- Lot/SN 必须来源于任务关联的生产报告；
- 质量未放行、被冻结、过期或处于召回中的 Lot/SN 禁止包装；
- SN 必须未装入其他有效 HU；
- Lot 数量包装时必须锁定可用未包装数量。

### 9.3 建箱与装箱

- 新建外箱后生成唯一箱码，状态为 `OPEN`；
- SN 管理：每次扫码增加 1 件，重复扫描幂等提示“已在当前箱”，扫描到其他箱则阻止；
- Lot 管理：扫描 Lot 后输入或从计数设备获取数量；数量必须大于 0；
- 禁止错物料、超任务、超箱容量和违反混批/混工单规则；
- 尾箱不足标准容量时，必须满足 `partial_package_allowed`，并记录尾箱原因；
- 每次成功扫码写操作日志，不依赖前端计数作为最终事实。

### 9.4 包装材料

- 按包装规格计算理论用量；
- 支持扫描包装材料 Lot，校验物料类型、质量和有效期；
- 封箱时记录实际用量和差异；超耗超过阈值需要班组长确认；
- 包装材料消耗可生成生产耗料或独立库存扣减流水，必须有幂等键。

### 9.5 称重、封箱与标签

- 称重可手工录入或通过设备适配接口上传；
- 保存毛重、皮重、净重、单位、设备号、操作人和时间；
- 超出规格上下限时禁止封箱，必须复称或创建异常；
- 封箱采用行锁/版本号校验，确保内容数量在校验后不被并发修改；
- 封箱成功后才允许打印正式标签；
- 打印记录包含模板版本、打印机、份数和业务快照；
- 补打必须填写原因；超过配置次数需要审批，旧标签可标记作废。

### 9.6 拆箱、移箱与返包

- 只有 `OPEN/REOPENED` 的 HU 可直接调整；
- 已封箱 HU 必须由授权人员执行“开箱”，记录原因和原标签作废；
- 移箱在一个事务内从原 HU 移除并加入目标 HU；
- 调整后重新校验容量、混批、混工单、重量和任务数量；
- 包装检验不合格时进入返包，保留原 HU、检验和标签历史。

### 9.7 组托与拆托

- 扫托码后连续扫描箱码加入托盘；
- 只能加入 `SEALED/RELEASED` 且未属于其他有效托盘的箱；
- 托盘容量、物料混装、客户/销售订单混装按包装规格控制；
- 封托后父子关系冻结；拆托需授权并记录原因。

### 9.8 包装检验与放行

- 检查项包含数量、标签、外观、封口、附件和重量；
- 必检规格封箱后自动创建包装检验；
- PASS 后 HU 进入 `RELEASED`；FAIL 后进入 `QUALITY_HOLD`，可关联 NCR；
- 任务所有 HU 均放行且数量守恒后，任务可转 `RELEASED_TO_STOCK`。

### 9.9 入库与发货

- 包装放行后按箱或托生成成品入库；库存仍以物料/Lot/库位记账，HU 作为库存维度和追溯对象；
- 同一 HU 只能成功入库一次；重复请求返回原库存流水；
- 发货扫描箱码/托码后自动展开内容并校验销售订单物料、数量、客户、Lot 状态、FEFO 和召回状态；
- 部分拆箱发货必须先将 HU 开箱并重新包装，不允许直接修改已封箱数量；
- 发货过账后 HU 状态为 `SHIPPED`，保存发货单和客户快照。

## 10. 数量守恒与并发控制

- 生产报告合格数量 = 未包装数量 + 包装中数量 + 已封箱数量 + 包装报废/隔离数量；
- HU 内容汇总必须等于 HU 实际数量；父 HU 数量由有效子 HU 汇总；
- 同一个 SN 同时只能属于一个未作废 HU；
- 同一 Lot 的累计包装数量不得超过来源可包装数量；
- 扫码、封箱、移箱、组托、入库和发货均支持 `idempotency_key`；
- 包装来源、HU 和库存结存更新使用 `SELECT ... FOR UPDATE` 或乐观版本号；
- 任何校验失败整次事务回滚，不留下半条内容、半个箱或重复库存流水。

## 11. API 设计

基础前缀：`/api/v1/mes/packaging`

### 11.1 包装规格

- `GET /specifications`
- `POST /specifications`
- `GET /specifications/{id}`
- `PUT /specifications/{id}`
- `POST /specifications/{id}/activate`
- `POST /specifications/{id}/deactivate`
- `POST /specifications/{id}/copy-version`

### 11.2 包装任务

- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{id}`
- `POST /tasks/{id}/release`
- `POST /tasks/{id}/start`
- `POST /tasks/{id}/suspend`
- `POST /tasks/{id}/cancel`
- `POST /tasks/{id}/close`
- `GET /tasks/{id}/scan-context`

### 11.3 箱码与托码

- `POST /tasks/{id}/handling-units`
- `GET /handling-units/{code}`
- `POST /handling-units/{id}/scan-item`
- `POST /handling-units/{id}/add-lot`
- `POST /handling-units/{id}/remove-content`
- `POST /handling-units/{id}/move-content`
- `POST /handling-units/{id}/weigh`
- `POST /handling-units/{id}/seal`
- `POST /handling-units/{id}/reopen`
- `POST /handling-units/{id}/void`
- `POST /handling-units/{id}/add-child`
- `POST /handling-units/{id}/remove-child`

### 11.4 标签、检验、入库与发货

- `POST /handling-units/{id}/labels/print`
- `POST /handling-units/{id}/labels/reprint`
- `POST /handling-units/{id}/inspections`
- `POST /inspections/{id}/complete`
- `POST /tasks/{id}/post-to-stock`
- `POST /shipments/{shipment_id}/scan-handling-unit`
- `GET /trace/handling-units/{code}`

所有写接口返回统一响应，并携带最新任务、HU 状态和数量摘要，供 PDA 连续扫码后即时刷新。

## 12. 前端页面

MES 制造管理新增“扫码包装”菜单，包含：

1. 包装任务：来源、产品、Lot、订单客户、计划/已包装/待包装数量和状态；
2. 包装工作台：大号扫码框、当前箱、装箱进度、最近扫码、声光反馈、封箱/换箱；
3. 箱托管理：箱码、托码、层级树、拆箱、移箱、组托、历史；
4. 称重与标签：重量结果、偏差、模板、打印和补打记录；
5. 包装检验：待检、PASS/FAIL、NCR 关联；
6. 包装追溯：箱码/托码 → Lot/SN → 工单/原料 → 发货/客户；
7. 包装规格：物料、客户、层级容量、混装策略、重量和标签配置。

PDA 模式要求：

- 输入框自动聚焦，扫码枪回车即提交；
- 成功、重复、警告、失败使用不同颜色和提示音；
- 显示当前箱装量、目标装量和剩余数量；
- 不以 Toast 作为唯一反馈，关键错误保留在页面；
- 网络断开时停止业务写入并显示未提交状态，不离线伪造封箱成功。

## 13. 权限

- `mes:packaging:view`
- `mes:packaging:spec`
- `mes:packaging:task`
- `mes:packaging:operate`
- `mes:packaging:seal`
- `mes:packaging:reopen`
- `mes:packaging:inspect`
- `mes:packaging:label`
- `mes:packaging:label-reprint-approve`
- `mes:packaging:post-stock`
- `mes:packaging:trace`

## 14. 稳定错误码

- `PACKAGING_SPEC_NOT_FOUND`
- `PACKAGING_SPEC_NOT_EFFECTIVE`
- `PACKAGING_SOURCE_NOT_COMPLETED`
- `PACKAGING_QUANTITY_EXCEEDS_AVAILABLE`
- `PACKAGING_TASK_NOT_OPERABLE`
- `PACKAGING_MATERIAL_MISMATCH`
- `PACKAGING_LOT_NOT_RELEASED`
- `PACKAGING_LOT_EXPIRED_OR_RECALLED`
- `PACKAGING_SERIAL_NOT_FOUND`
- `PACKAGING_SERIAL_ALREADY_PACKED`
- `PACKAGING_CAPACITY_EXCEEDED`
- `PACKAGING_MIXED_LOT_FORBIDDEN`
- `PACKAGING_MIXED_ORDER_FORBIDDEN`
- `PACKAGING_WEIGHT_REQUIRED`
- `PACKAGING_WEIGHT_OUT_OF_TOLERANCE`
- `HANDLING_UNIT_NOT_FOUND`
- `HANDLING_UNIT_NOT_OPEN`
- `HANDLING_UNIT_ALREADY_SEALED`
- `HANDLING_UNIT_ALREADY_PARENTED`
- `HANDLING_UNIT_CONTENT_NOT_EMPTY`
- `PACKAGING_INSPECTION_REQUIRED`
- `PACKAGING_NOT_RELEASED`
- `PACKAGING_ALREADY_POSTED`
- `PACKAGING_LABEL_REPRINT_APPROVAL_REQUIRED`

错误码通过现有 `api_errors`/`ui_tips` 双语业务字典配置中英文提示。

## 15. 集成关系

- 生产：读取工单和生产报告，不修改历史完工数量；
- 质量：包装前校验 Lot/SN 放行，包装不合格可创建 NCR；
- 追溯：新增 HU 与 Lot/SN、工单、发货之间的追溯关系；
- 库存：包装入库和发货统一调用库存服务，禁止绕过质量、效期与隔离门禁；
- 销售：客户和销售订单决定包装规格优先级；
- 召回：从 Lot/SN 展开到箱、托、库存库位、发货单和客户；
- 成本：记录包装材料实际消耗和人工/设备工时，为后续工单包装成本归集提供来源。

## 16. 非功能要求

- 单次扫码接口 P95 响应时间不高于 500 ms（不含外部打印机耗时）；
- 同一包装任务支持至少 10 个终端并发，不得重复包装同一 SN；
- 所有时间保存为项目统一时区类型；数量使用 Decimal；
- 包装内容、标签和状态变更不可物理删除；
- 关键操作保存用户、终端、工位、设备、时间、原值和新值；
- MySQL 为正式数据库基线，Migration 必须支持升级、降级和再次升级；
- 中英文切换后页面标题、字段、状态、错误和扫码提示同步切换。

## 17. 验收场景

1. Lot 产品按标准装量连续装箱，满箱后称重、封箱、打印标签并入库；
2. SN 产品重复扫码时不重复计数，扫描已在其他箱的 SN 被阻止；
3. 扫描错物料、冻结/过期/召回 Lot、未放行产品时无法装箱；
4. 禁止超箱容量；允许尾箱时能记录尾箱原因并正常封箱；
5. 禁止违反混批、混工单和客户专用包装规则；
6. 超重或欠重时不能封箱，复称合格后可继续；
7. 封箱后不能修改内容；授权开箱、移箱和返包保留完整历史；
8. 箱可组托，重复组托被拒绝，封托后层级冻结；
9. 包装检验 FAIL 后 HU 隔离，PASS 后才可入库或发货；
10. 发货扫描托码可展开所有箱和内容，数量及销售订单校验正确；
11. 通过箱码可追溯产品 Lot/SN、生产工单、原材料 Lot、发货单和客户；
12. 重复扫码、封箱、入库和发货请求满足幂等，数据库数量守恒；
13. MySQL 集成测试、并发测试、后端测试、前端类型检查和生产构建全部通过。

## 18. 实施阶段

### 第一阶段：核心装箱闭环

- 包装规格、包装任务、HU/内容模型；
- Lot/SN 扫码、容量/质量校验；
- 称重、封箱、标签记录；
- 包装工作台、权限、审计和 MySQL 验证。

### 第二阶段：仓储交付与质量闭环

- 组托/拆托；
- 包装检验、NCR 和返包；
- 扫箱/扫托入库与销售发货；
- HU 全链路追溯和召回影响展开。

### 第三阶段：设备与成本扩展

- 电子秤、打印机和自动包装设备适配；
- 包装材料自动领用、超耗预警；
- 包装工时、设备费用和产品包装成本分析。

## 19. Definition of Done

- PRD 对应的 Migration、模型、Schema、Service、API、菜单和权限完成；
- PC/PDA 包装工作台可连续扫码；
- 包装数量守恒、并发防重和幂等规则有自动化测试；
- 完工 → 包装 → 质检 → 入库 → 发货 → 追溯闭环在真实 MySQL 事务中通过；
- 双语字段、状态和提示完整；
- 前端类型检查、生产构建和全量后端测试通过。
