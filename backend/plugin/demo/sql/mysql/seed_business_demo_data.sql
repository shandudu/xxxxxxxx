-- DEMO business data snapshot for MySQL 8.0
-- Generated from the validated local `fba` database after running:
--   scripts/validate_manufacturing_happy_path_rollback.py --commit
--   scripts/validate_sales_order_driven_happy_path.py --commit
--
-- Scope: supplier/customer master data, material/BOM/routing, purchasing and
-- receipt, lot and inventory ledger, MPS/MRP, work orders and execution,
-- quality inspection, lot traceability, sales order and shipment.
--
-- IMPORTANT:
-- 1. This is a relational snapshot containing original numeric IDs. Import it
--    only into a clean development/demo MySQL database created from this
--    project's schema and baseline initialization data.
-- 2. Do not import it into production or a database that already has business
--    data. Use the repeatable demo API/service instead in those environments.
-- 3. The two scenario keys are MANUFACTURING_HAPPY_PATH and
--    SALES_ORDER_DRIVEN_HAPPY_PATH; all business records are identifiable by
--    `DEMO-*` codes and `MES_DEMO:*` remarks.

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

/*!40000 ALTER TABLE `mes_demo_run` DISABLE KEYS */;
INSERT INTO `mes_demo_run` (`id`, `run_no`, `scenario_code`, `status`, `started_at`, `completed_at`, `failed_step`, `error_message`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,'DEMO-0AF4A41CE36F','MANUFACTURING_HAPPY_PATH','COMPLETED','2026-08-20 23:05:24','2026-08-20 23:05:24',NULL,NULL,NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(227,'DEMO-SOD-1F92ADB7686F','SALES_ORDER_DRIVEN_HAPPY_PATH','COMPLETED','2026-09-05 21:31:28','2026-09-05 21:31:30',NULL,NULL,NULL,NULL,'2026-09-05 21:31:28','2026-09-05 21:31:30',0,NULL);
/*!40000 ALTER TABLE `mes_demo_run` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_unit` DISABLE KEYS */;
INSERT INTO `mes_unit` (`id`, `unit_code`, `unit_name`, `symbol`, `status`, `decimal_places`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'PCS','件','pcs','ACTIVE',0,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(2,'KG','千克','kg','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(3,'G','克','g','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(4,'T','吨','t','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(5,'M','米','m','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(6,'MM','毫米','mm','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(7,'L','升','L','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(8,'ML','毫升','ml','ACTIVE',3,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(9,'BOX','箱','box','ACTIVE',0,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(10,'ROLL','卷','roll','ACTIVE',0,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(11,'SET','套','set','ACTIVE',0,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(19,'DEMO-EA','演示件','EA','ACTIVE',0,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_unit` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material_category` DISABLE KEYS */;
INSERT INTO `mes_material_category` (`id`, `category_code`, `category_name`, `parent_id`, `status`, `sort_no`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'RAW','原材料',NULL,'ACTIVE',10,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(2,'SEMI','半成品',NULL,'ACTIVE',20,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(3,'FG','成品',NULL,'ACTIVE',30,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(4,'AUX','辅料',NULL,'ACTIVE',40,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(5,'PACK','包装材料',NULL,'ACTIVE',50,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(6,'SPARE','备品备件',NULL,'ACTIVE',60,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(7,'CONSUMABLE','耗材',NULL,'ACTIVE',70,NULL,'2026-08-08 18:06:58',NULL,0,NULL),(15,'DEMO-MFG','演示制造物料',NULL,'ACTIVE',0,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_material_category` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_warehouse` DISABLE KEYS */;
INSERT INTO `mes_warehouse` (`id`, `warehouse_code`, `warehouse_name`, `warehouse_type`, `factory_code`, `status`, `allow_inbound`, `allow_outbound`, `remark`, `sort_no`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,'DEMO-WH-001','演示制造仓','RAW_MATERIAL',NULL,'ACTIVE',1,1,'MES_DEMO:MANUFACTURING_HAPPY_PATH',0,NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_warehouse` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_area` DISABLE KEYS */;
INSERT INTO `mes_area` (`id`, `area_code`, `area_name`, `warehouse_id`, `area_type`, `status`, `remark`, `sort_no`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,'DEMO-AREA-001','演示收发区',3,'NORMAL','ACTIVE','MES_DEMO:MANUFACTURING_HAPPY_PATH',0,'2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_area` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_location` DISABLE KEYS */;
INSERT INTO `mes_location` (`id`, `location_code`, `location_name`, `warehouse_id`, `area_id`, `location_type`, `parent_id`, `location_level`, `status`, `storage_enabled`, `capacity_value`, `capacity_unit`, `mixed_material_allowed`, `mixed_lot_allowed`, `remark`, `sort_no`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,'DEMO-LOC-001','演示库位',3,3,'BIN',NULL,1,'AVAILABLE',1,NULL,NULL,1,1,'MES_DEMO:MANUFACTURING_HAPPY_PATH',0,'2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_location` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material` DISABLE KEYS */;
INSERT INTO `mes_material` (`id`, `material_code`, `material_name`, `material_type`, `category_id`, `base_unit_id`, `material_short_name`, `specification`, `model`, `status`, `batch_control`, `serial_control`, `purchasable`, `producible`, `sellable`, `quality_inspection_required`, `default_warehouse_id`, `shelf_life_days`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (13,'DEMO-RM-001','演示原材料','RAW_MATERIAL',15,19,NULL,NULL,NULL,'ACTIVE',1,0,1,0,0,0,3,NULL,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL),(14,'DEMO-FG-001','演示成品','FINISHED_PRODUCT',15,19,NULL,NULL,NULL,'ACTIVE',1,0,0,1,1,1,3,NULL,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL),(457,'DEMO-SOD-RM-001','销售驱动演示原材料','RAW_MATERIAL',15,19,NULL,NULL,NULL,'ACTIVE',1,0,1,0,0,0,3,NULL,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:28',NULL,0,NULL),(458,'DEMO-SOD-FG-001','销售驱动演示成品','FINISHED_PRODUCT',15,19,NULL,NULL,NULL,'ACTIVE',1,0,0,1,1,1,3,NULL,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:28',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_material` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_supplier_category` DISABLE KEYS */;
INSERT INTO `erp_supplier_category` (`id`, `category_code`, `category_name`, `parent_id`, `status`, `sort_no`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (5,'DEMO-SUP-CAT','演示供应商分类',NULL,'ACTIVE',0,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_supplier_category` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_supplier` DISABLE KEYS */;
INSERT INTO `erp_supplier` (`id`, `supplier_code`, `supplier_name`, `category_id`, `supplier_type`, `company_type`, `short_name`, `unified_social_credit_code`, `tax_number`, `registered_address`, `business_address`, `website`, `country`, `province`, `city`, `currency`, `payment_terms`, `default_lead_time_days`, `purchasing_enabled`, `quality_enabled`, `trace_enabled`, `preferred`, `status`, `cooperation_status`, `quality_status`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,'DEMO-SUP-001','演示原料供应商',5,'MATERIAL','COMPANY',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'CNY',NULL,NULL,1,1,1,0,'ACTIVE','NORMAL','QUALIFIED','MES_DEMO:MANUFACTURING_HAPPY_PATH',1,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL);
/*!40000 ALTER TABLE `erp_supplier` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_customer_category` DISABLE KEYS */;
INSERT INTO `erp_customer_category` (`id`, `category_code`, `category_name`, `parent_id`, `status`, `sort_no`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DOMESTIC','国内客户',NULL,'ACTIVE',10,NULL,'2026-08-09 17:59:58',NULL,0,NULL),(2,'OVERSEAS','海外客户',NULL,'ACTIVE',20,NULL,'2026-08-09 17:59:58',NULL,0,NULL),(3,'DISTRIBUTOR','经销商',NULL,'ACTIVE',30,NULL,'2026-08-09 17:59:58',NULL,0,NULL),(4,'INTERNAL','内部客户',NULL,'ACTIVE',40,NULL,'2026-08-09 17:59:58',NULL,0,NULL),(5,'DEMO-CUS-CAT','演示客户分类',NULL,'ACTIVE',0,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_customer_category` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_customer` DISABLE KEYS */;
INSERT INTO `erp_customer` (`id`, `customer_code`, `customer_name`, `customer_type`, `short_name`, `category_id`, `company_type`, `unified_social_credit_code`, `tax_number`, `country`, `province`, `city`, `registered_address`, `website`, `status`, `cooperation_status`, `sales_enabled`, `shipment_enabled`, `trace_enabled`, `preferred`, `default_currency`, `payment_term`, `delivery_term`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-CUS-001','演示成品客户','ENTERPRISE',NULL,5,'COMPANY',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACTIVE','NORMAL',1,1,1,0,NULL,NULL,NULL,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_customer` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_operation` DISABLE KEYS */;
INSERT INTO `mes_operation` (`id`, `operation_code`, `operation_name`, `operation_type`, `status`, `description`, `default_standard_time`, `time_unit`, `quality_required_default`, `key_operation_default`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `operation_short_name`, `production_enabled`, `quality_enabled`, `trace_enabled`, `sort_no`) VALUES (4,'DEMO-OP-001','演示装配','ASSEMBLY','ACTIVE',NULL,NULL,'MIN',0,0,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL,NULL,1,1,1,0);
/*!40000 ALTER TABLE `mes_operation` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_work_center` DISABLE KEYS */;
INSERT INTO `mes_work_center` (`id`, `work_center_code`, `work_center_name`, `work_center_type`, `status`, `factory_code`, `line_code`, `capacity_type`, `standard_capacity`, `capacity_unit`, `calendar_code`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `workshop_code`, `location_description`, `production_enabled`, `scheduling_enabled`, `capacity_value`, `parallel_capacity`, `sort_no`) VALUES (7,'DEMO-WC-001','演示装配单元','CELL','ACTIVE',NULL,NULL,NULL,NULL,'EA/H',NULL,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL,NULL,NULL,1,1,60.000000,1,0);
/*!40000 ALTER TABLE `mes_work_center` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_bom` DISABLE KEYS */;
INSERT INTO `mes_bom` (`id`, `bom_code`, `product_material_id`, `bom_version`, `base_quantity`, `status`, `effective_from`, `effective_to`, `is_default`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (6,'DEMO-BOM-FG-001',14,'V1',1.000000,'ACTIVE',NULL,NULL,0,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(228,'DEMO-SOD-BOM-FG-001',458,'V1',1.000000,'ACTIVE',NULL,NULL,0,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:28','2026-09-05 21:31:28',0,NULL);
/*!40000 ALTER TABLE `mes_bom` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_bom_item` DISABLE KEYS */;
INSERT INTO `mes_bom_item` (`id`, `bom_id`, `line_no`, `component_material_id`, `quantity`, `unit_id`, `loss_rate`, `fixed_loss_qty`, `is_optional`, `remark`, `sort_no`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (4,6,10,13,1.000000,19,0.0000,0.000000,0,'MES_DEMO:MANUFACTURING_HAPPY_PATH',0,'2026-08-20 23:05:24',NULL,0,NULL),(226,228,10,457,1.000000,19,0.0000,0.000000,0,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',0,'2026-09-05 21:31:28',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_bom_item` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_routing` DISABLE KEYS */;
INSERT INTO `mes_routing` (`id`, `routing_code`, `routing_name`, `product_material_id`, `routing_version`, `routing_type`, `base_quantity`, `status`, `effective_from`, `effective_to`, `is_default`, `description`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (5,'DEMO-RT-FG-001','演示成品标准工艺',14,'V1','STANDARD',1.000000,'ACTIVE',NULL,NULL,1,NULL,'MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(227,'DEMO-SOD-RT-FG-001','销售驱动演示成品工艺',458,'V1','STANDARD',1.000000,'ACTIVE',NULL,NULL,1,NULL,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:28','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_routing` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_routing_operation` DISABLE KEYS */;
INSERT INTO `mes_routing_operation` (`id`, `routing_id`, `sequence_no`, `operation_id`, `work_center_id`, `operation_name_override`, `operation_name_snapshot`, `setup_time_min`, `run_time_value`, `run_time_unit`, `queue_time_min`, `move_time_min`, `standard_yield_rate`, `reporting_required`, `quality_required`, `trace_required`, `remark`, `sort_no`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (4,5,10,4,7,NULL,'演示装配',0.0000,1.000000,'MIN_PER_BASE_QTY',0.0000,0.0000,100.0000,1,0,1,'MES_DEMO:MANUFACTURING_HAPPY_PATH',0,NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL),(226,227,10,4,7,NULL,'演示装配',0.0000,1.000000,'MIN_PER_BASE_QTY',0.0000,0.0000,100.0000,1,0,1,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',0,NULL,NULL,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_routing_operation` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_sales_order` DISABLE KEYS */;
INSERT INTO `erp_sales_order` (`id`, `sales_order_no`, `customer_id`, `customer_code_snapshot`, `customer_name_snapshot`, `status`, `currency`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `requested_delivery_at`) VALUES (1,'DEMO-SO-001',1,'DEMO-CUS-001','演示成品客户','SHIPPED','CNY','MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL,NULL),(225,'DEMO-SOD-SO-001',1,'DEMO-CUS-001','演示成品客户','SHIPPED','CNY','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29','2026-09-05 21:31:30',0,NULL,NULL);
/*!40000 ALTER TABLE `erp_sales_order` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_sales_order_line` DISABLE KEYS */;
INSERT INTO `erp_sales_order_line` (`id`, `sales_order_id`, `line_no`, `material_id`, `unit_id`, `ordered_quantity`, `material_code_snapshot`, `material_name_snapshot`, `unit_code_snapshot`, `shipped_quantity`, `unit_price`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,1,1,14,19,10.000000,'DEMO-FG-001','演示成品','DEMO-EA',10.000000,10.000000,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(225,225,1,458,19,10.000000,'DEMO-SOD-FG-001','销售驱动演示成品','DEMO-EA',10.000000,10.000000,'2026-09-05 21:31:29','2026-09-05 21:31:30',0,NULL);
/*!40000 ALTER TABLE `erp_sales_order_line` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_mps_plan` DISABLE KEYS */;
INSERT INTO `mes_mps_plan` (`plan_no`, `plan_name`, `horizon_start`, `horizon_end`, `status`, `remark`, `id`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES ('DEMO-SOD-MPS-001','销售订单驱动演示计划','2026-09-05','2026-10-05','CONFIRMED','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',225,NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_mps_plan` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_mps_demand` DISABLE KEYS */;
INSERT INTO `mes_mps_demand` (`mps_plan_id`, `line_no`, `material_id`, `unit_id`, `demand_date`, `quantity`, `material_code_snapshot`, `material_name_snapshot`, `unit_code_snapshot`, `demand_type`, `source_id`, `source_no`, `remark`, `id`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (225,1,458,19,'2026-09-12',10.000000,'DEMO-SOD-FG-001','销售驱动演示成品','DEMO-EA','SALES_ORDER',225,'DEMO-SOD-SO-001/1',NULL,225,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_mps_demand` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_mrp_run` DISABLE KEYS */;
INSERT INTO `mes_mrp_run` (`run_no`, `mps_plan_id`, `status`, `include_inventory`, `include_open_purchase`, `include_open_production`, `default_purchase_lead_days`, `default_production_lead_days`, `max_level`, `requirement_count`, `planned_order_count`, `error_message`, `started_at`, `completed_at`, `id`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `promise_refresh_at`, `promise_assessment_count`) VALUES ('MRP-20260905213128-469803',225,'COMPLETED',1,1,1,7,1,20,2,2,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',225,NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL,'2026-09-05 21:31:29',1);
/*!40000 ALTER TABLE `mes_mrp_run` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_mrp_requirement` DISABLE KEYS */;
INSERT INTO `mes_mrp_requirement` (`mrp_run_id`, `sequence_no`, `mps_demand_id`, `level_no`, `material_id`, `requirement_date`, `gross_requirement`, `material_code_snapshot`, `material_name_snapshot`, `unit_code_snapshot`, `source_path`, `on_hand_allocated`, `purchase_supply_allocated`, `production_supply_allocated`, `net_requirement`, `planned_order_quantity`, `uncovered_quantity`, `parent_material_id`, `bom_id`, `bom_item_id`, `id`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (225,1,225,0,458,'2026-09-12',10.000000,'DEMO-SOD-FG-001','销售驱动演示成品','DEMO-EA','DEMO-SOD-FG-001',0.000000,0.000000,0.000000,10.000000,10.000000,0.000000,NULL,NULL,NULL,449,'2026-09-05 21:31:29',NULL,0,NULL),(225,2,225,1,457,'2026-09-11',10.000000,'DEMO-SOD-RM-001','销售驱动演示原材料','DEMO-EA','DEMO-SOD-FG-001 > DEMO-SOD-RM-001',0.000000,0.000000,0.000000,10.000000,10.000000,0.000000,458,228,226,450,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_mrp_requirement` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_planned_order` DISABLE KEYS */;
INSERT INTO `mes_planned_order` (`planned_order_no`, `mrp_run_id`, `mrp_requirement_id`, `sequence_no`, `material_id`, `order_type`, `quantity`, `release_date`, `due_date`, `material_code_snapshot`, `material_name_snapshot`, `unit_code_snapshot`, `status`, `bom_id`, `source_document_type`, `source_document_id`, `source_document_no`, `firmed_at`, `firmed_by`, `released_at`, `released_by`, `remark`, `id`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES ('MPO-225-00001-0554',225,449,1,458,'PRODUCTION',10.000000,'2026-09-11','2026-09-12','DEMO-SOD-FG-001','销售驱动演示成品','DEMO-EA','RELEASED',228,'WORK_ORDER',248,'WO-20260905213128-508918',NULL,NULL,'2026-09-05 21:31:29',NULL,NULL,449,NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL),('MPO-225-00002-8BD0',225,450,2,457,'PURCHASE',10.000000,'2026-09-04','2026-09-11','DEMO-SOD-RM-001','销售驱动演示原材料','DEMO-EA','RELEASED',NULL,'PURCHASE_ORDER',254,'PO-20260905213128-6886BB',NULL,NULL,'2026-09-05 21:31:29',NULL,NULL,450,NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_planned_order` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_purchase_order` DISABLE KEYS */;
INSERT INTO `erp_purchase_order` (`id`, `purchase_order_no`, `supplier_id`, `supplier_code_snapshot`, `supplier_name_snapshot`, `status`, `currency`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (2,'DEMO-PO-001',3,'DEMO-SUP-001','演示原料供应商','RECEIVED','CNY','MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(254,'PO-20260905213128-6886BB',3,'DEMO-SUP-001','演示原料供应商','RECEIVED','CNY','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `erp_purchase_order` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_purchase_order_line` DISABLE KEYS */;
INSERT INTO `erp_purchase_order_line` (`id`, `purchase_order_id`, `line_no`, `material_id`, `unit_id`, `ordered_quantity`, `material_code_snapshot`, `material_name_snapshot`, `unit_code_snapshot`, `unit_name_snapshot`, `received_quantity`, `unit_price`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `requested_delivery_at`, `supplier_confirmed_delivery_at`) VALUES (2,2,1,13,19,10.000000,'DEMO-RM-001','演示原材料','DEMO-EA','演示件',10.000000,1.000000,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL,NULL,NULL),(251,254,1,457,19,10.000000,'DEMO-SOD-RM-001','销售驱动演示原材料','DEMO-EA','演示件',10.000000,1.000000,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL,'2026-09-11 00:00:00',NULL);
/*!40000 ALTER TABLE `erp_purchase_order_line` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_supplier_receipt` DISABLE KEYS */;
INSERT INTO `erp_supplier_receipt` (`id`, `receipt_no`, `purchase_order_id`, `supplier_id`, `supplier_code_snapshot`, `supplier_name_snapshot`, `status`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-RCV-001',2,3,'DEMO-SUP-001','演示原料供应商','POSTED','MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL),(223,'DEMO-SOD-RCV-001',254,3,'DEMO-SUP-001','演示原料供应商','POSTED','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_supplier_receipt` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_supplier_receipt_line` DISABLE KEYS */;
INSERT INTO `erp_supplier_receipt_line` (`id`, `supplier_receipt_id`, `purchase_order_line_id`, `line_no`, `material_id`, `warehouse_id`, `location_id`, `quantity`, `material_code_snapshot`, `material_name_snapshot`, `warehouse_code_snapshot`, `location_code_snapshot`, `stock_transaction_id`, `lot_id`, `lot_no_snapshot`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,1,2,1,13,3,3,10.000000,'DEMO-RM-001','演示原材料','DEMO-WH-001','DEMO-LOC-001',1,1,'DEMO-RM-LOT-001',NULL,'2026-08-20 23:05:24',NULL,0,NULL),(222,223,251,1,457,3,3,10.000000,'DEMO-SOD-RM-001','销售驱动演示原材料','DEMO-WH-001','DEMO-LOC-001',1036,468,'DEMO-SOD-RM-LOT-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_supplier_receipt_line` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material_lot` DISABLE KEYS */;
INSERT INTO `mes_material_lot` (`id`, `lot_no`, `material_id`, `lot_type`, `source_type`, `source_ref_id`, `source_ref_no`, `parent_lot_id`, `production_date`, `expiry_date`, `quantity`, `unit_id`, `status`, `quality_status`, `supplier_lot_no`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-RM-LOT-001',13,'SUPPLIER','PURCHASE_RECEIPT',1,'DEMO-RCV-001',NULL,NULL,NULL,10.000000,19,'ACTIVE','PASS','SUP-LOT-001',NULL,NULL,NULL,'2026-08-20 23:05:24',NULL,0,NULL),(2,'DEMO-FG-LOT-001',14,'FINISHED','WORK_ORDER',5,'DEMO-WO-001',NULL,NULL,NULL,10.000000,19,'ACTIVE','PASS',NULL,NULL,NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(468,'DEMO-SOD-RM-LOT-001',457,'SUPPLIER','PURCHASE_RECEIPT',223,'DEMO-SOD-RCV-001',NULL,NULL,NULL,10.000000,19,'ACTIVE','PASS','SOD-SUP-LOT-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:29',NULL,0,NULL),(469,'DEMO-SOD-FG-LOT-001',458,'FINISHED','WORK_ORDER',248,'WO-20260905213128-508918',NULL,NULL,NULL,10.000000,19,'ACTIVE','PASS',NULL,NULL,NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_material_lot` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_inventory_balance` DISABLE KEYS */;
INSERT INTO `mes_inventory_balance` (`id`, `balance_key`, `material_id`, `warehouse_id`, `location_id`, `lot_id`, `quantity`, `reserved_quantity`, `version`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'13:1:3:3',13,3,3,1,0.000000,0.000000,2,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(2,'14:2:3:3',14,3,3,2,0.000000,0.000000,2,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(452,'457:468:3:3',457,3,3,468,0.000000,0.000000,2,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL),(453,'458:469:3:3',458,3,3,469,0.000000,0.000000,2,'2026-09-05 21:31:29','2026-09-05 21:31:30',0,NULL);
/*!40000 ALTER TABLE `mes_inventory_balance` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_stock_transaction` DISABLE KEYS */;
INSERT INTO `mes_stock_transaction` (`id`, `transaction_no`, `idempotency_key`, `transaction_type`, `material_id`, `warehouse_id`, `location_id`, `quantity_delta`, `balance_after`, `lot_id`, `reference_type`, `reference_id`, `reference_no`, `remark`, `operator_id`, `occurred_at`) VALUES (1,'STX-20260820230524-B49D7D24','SUPPLIER_RECEIPT:1:1','RECEIPT',13,3,3,10.000000,10.000000,1,'SUPPLIER_RECEIPT',1,'DEMO-RCV-001',NULL,1,'2026-08-20 23:05:24'),(2,'STX-20260820230524-7A2C9FD1','MATERIAL_ISSUE:1:1','ISSUE',13,3,3,-10.000000,0.000000,1,'MATERIAL_ISSUE',1,'DEMO-ISS-001','MES_DEMO:MANUFACTURING_HAPPY_PATH',1,'2026-08-20 23:05:24'),(3,'STX-20260820230524-7CAA848B','PRODUCTION_REPORT:5:DEMO-RPT-001','PRODUCTION_RECEIPT',14,3,3,10.000000,10.000000,2,'PRODUCTION_REPORT',5,'DEMO-RPT-001','MES_DEMO:MANUFACTURING_HAPPY_PATH',1,'2026-08-20 23:05:24'),(4,'STX-20260820230524-BF6EC38E','SHIPMENT:1:1','SHIPMENT',14,3,3,-10.000000,0.000000,2,'SHIPMENT',1,'DEMO-SHP-001','MES_DEMO:MANUFACTURING_HAPPY_PATH',1,'2026-08-20 23:05:24'),(1036,'STX-20260905213128-42110ABF','SUPPLIER_RECEIPT:223:1','RECEIPT',457,3,3,10.000000,10.000000,468,'SUPPLIER_RECEIPT',223,'DEMO-SOD-RCV-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,'2026-09-05 21:31:29'),(1037,'STX-20260905213129-91282F33','MATERIAL_ISSUE:221:1','ISSUE',457,3,3,-10.000000,0.000000,468,'MATERIAL_ISSUE',221,'DEMO-SOD-ISS-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,'2026-09-05 21:31:29'),(1038,'STX-20260905213129-C15C6BAE','PRODUCTION_REPORT:248:DEMO-SOD-RPT-001','PRODUCTION_RECEIPT',458,3,3,10.000000,10.000000,469,'PRODUCTION_REPORT',248,'DEMO-SOD-RPT-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,'2026-09-05 21:31:29'),(1039,'STX-20260905213129-DA637F93','SHIPMENT:222:1','SHIPMENT',458,3,3,-10.000000,0.000000,469,'SHIPMENT',222,'DEMO-SOD-SHP-001','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,'2026-09-05 21:31:30');
/*!40000 ALTER TABLE `mes_stock_transaction` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_work_order` DISABLE KEYS */;
INSERT INTO `mes_work_order` (`id`, `work_order_no`, `product_material_id`, `bom_id`, `routing_id`, `planned_quantity`, `product_code_snapshot`, `product_name_snapshot`, `bom_code_snapshot`, `bom_version_snapshot`, `routing_code_snapshot`, `routing_version_snapshot`, `status`, `completed_quantity`, `scrap_quantity`, `planned_start_at`, `planned_end_at`, `started_at`, `completed_at`, `remark`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (5,'DEMO-WO-001',14,6,5,10.000000,'DEMO-FG-001','演示成品','DEMO-BOM-FG-001','V1','DEMO-RT-FG-001','V1','COMPLETED',10.000000,0.000000,NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24','MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(248,'WO-20260905213128-508918',458,228,227,10.000000,'DEMO-SOD-FG-001','销售驱动演示成品','DEMO-SOD-BOM-FG-001','V1','DEMO-SOD-RT-FG-001','V1','COMPLETED',10.000000,0.000000,'2026-09-11 00:00:00','2026-09-12 00:00:00','2026-09-05 21:31:29','2026-09-05 21:31:29','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_work_order` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_work_order_operation` DISABLE KEYS */;
INSERT INTO `mes_work_order_operation` (`id`, `work_order_id`, `sequence_no`, `operation_id`, `operation_code_snapshot`, `operation_name_snapshot`, `work_center_id`, `status`, `completed_quantity`, `scrap_quantity`, `started_at`, `completed_at`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (4,5,10,4,'DEMO-OP-001','演示装配',7,'COMPLETED',10.000000,0.000000,'2026-08-20 23:05:24','2026-08-20 23:05:24','2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(247,248,10,4,'DEMO-OP-001','演示装配',7,'COMPLETED',10.000000,0.000000,'2026-09-05 21:31:29','2026-09-05 21:31:29','2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_work_order_operation` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_work_order_material_requirement` DISABLE KEYS */;
INSERT INTO `mes_work_order_material_requirement` (`id`, `work_order_id`, `line_no`, `bom_item_id`, `material_id`, `unit_id`, `required_quantity`, `material_code_snapshot`, `material_name_snapshot`, `work_order_operation_id`, `issued_quantity`, `returned_quantity`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (3,5,10,4,13,19,10.000000,'DEMO-RM-001','演示原材料',NULL,10.000000,0.000000,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(246,248,10,226,457,19,10.000000,'DEMO-SOD-RM-001','销售驱动演示原材料',NULL,10.000000,0.000000,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_work_order_material_requirement` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material_issue` DISABLE KEYS */;
INSERT INTO `mes_material_issue` (`id`, `issue_no`, `work_order_id`, `status`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-ISS-001',5,'POSTED','MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL),(221,'DEMO-SOD-ISS-001',248,'POSTED','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_material_issue` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material_issue_line` DISABLE KEYS */;
INSERT INTO `mes_material_issue_line` (`id`, `issue_id`, `requirement_id`, `material_id`, `warehouse_id`, `location_id`, `quantity`, `stock_transaction_id`, `lot_id`, `returned_quantity`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,1,3,13,3,3,10.000000,2,1,0.000000,'2026-08-20 23:05:24',NULL,0,NULL),(221,221,246,457,3,3,10.000000,1037,468,0.000000,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_material_issue_line` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_production_execution` DISABLE KEYS */;
INSERT INTO `mes_production_execution` (`id`, `execution_no`, `work_order_id`, `work_order_operation_id`, `started_at`, `status`, `good_quantity`, `scrap_quantity`, `completed_at`, `operator_id`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (2,'DEMO-EXE-001',5,4,'2026-08-20 23:05:24','COMPLETED',10.000000,0.000000,'2026-08-20 23:05:24',1,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(223,'DEMO-SOD-EXE-001',248,247,'2026-09-05 21:31:29','COMPLETED',10.000000,0.000000,'2026-09-05 21:31:29',NULL,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_production_execution` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_material_consumption` DISABLE KEYS */;
INSERT INTO `mes_material_consumption` (`id`, `consumption_no`, `execution_id`, `requirement_id`, `material_id`, `quantity`, `consumed_at`, `issue_line_id`, `lot_id`, `operator_id`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-CON-001',2,3,13,10.000000,'2026-08-20 23:05:24',1,1,1,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL),(221,'DEMO-SOD-CON-001',223,246,457,10.000000,'2026-09-05 21:31:29',221,468,NULL,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_material_consumption` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_production_report` DISABLE KEYS */;
INSERT INTO `mes_production_report` (`id`, `report_no`, `work_order_id`, `good_quantity`, `scrap_quantity`, `warehouse_id`, `location_id`, `stock_transaction_id`, `lot_id`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `idempotency_key`) VALUES (1,'DEMO-RPT-001',5,10.000000,0.000000,3,3,3,2,'MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL,NULL),(242,'DEMO-SOD-RPT-001',248,10.000000,0.000000,3,3,1038,469,'MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:29',NULL,0,NULL,NULL);
/*!40000 ALTER TABLE `mes_production_report` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_quality_inspection` DISABLE KEYS */;
INSERT INTO `mes_quality_inspection` (`id`, `inspection_no`, `inspection_type`, `material_id`, `sample_quantity`, `status`, `lot_id`, `parent_inspection_id`, `source_type`, `source_id`, `source_no`, `accepted_quantity`, `rejected_quantity`, `result`, `inspected_at`, `inspector_id`, `conclusion`, `created_by`, `updated_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'DEMO-QI-001','FINAL',14,10.000000,'COMPLETED',2,NULL,'PRODUCTION_REPORT',5,'DEMO-RPT-001',10.000000,0.000000,'PASS','2026-08-20 23:05:24',1,'演示成品检验合格',NULL,NULL,'2026-08-20 23:05:24','2026-08-20 23:05:24',0,NULL),(413,'DEMO-SOD-QI-001','FINAL',458,10.000000,'COMPLETED',469,NULL,'PRODUCTION_REPORT',242,'DEMO-SOD-RPT-001',10.000000,0.000000,'PASS','2026-09-05 21:31:29',NULL,'销售驱动演示终检合格',NULL,NULL,'2026-09-05 21:31:29','2026-09-05 21:31:29',0,NULL);
/*!40000 ALTER TABLE `mes_quality_inspection` ENABLE KEYS */;

/*!40000 ALTER TABLE `mes_trace_relation` DISABLE KEYS */;
INSERT INTO `mes_trace_relation` (`id`, `source_type`, `source_id`, `source_code`, `target_type`, `target_id`, `target_code`, `relation_type`, `quantity`, `unit_id`, `operation_ref_id`, `business_ref_type`, `business_ref_id`, `business_ref_no`, `business_ref_key`, `remark`, `created_by`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,'LOT',1,'DEMO-RM-LOT-001','LOT',2,'DEMO-FG-LOT-001','CONSUMED_TO',10.000000,19,NULL,'WORK_ORDER',5,'DEMO-WO-001','WORK_ORDER|5|DEMO-WO-001','MES_DEMO:MANUFACTURING_HAPPY_PATH',NULL,'2026-08-20 23:05:24',NULL,0,NULL),(236,'LOT',468,'DEMO-SOD-RM-LOT-001','LOT',469,'DEMO-SOD-FG-LOT-001','CONSUMED_TO',10.000000,19,NULL,'WORK_ORDER',248,'WO-20260905213128-508918','WORK_ORDER|248|WO-20260905213128-508918','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH',NULL,'2026-09-05 21:31:29',NULL,0,NULL);
/*!40000 ALTER TABLE `mes_trace_relation` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_shipment` DISABLE KEYS */;
INSERT INTO `erp_shipment` (`id`, `shipment_no`, `sales_order_id`, `customer_id`, `customer_code_snapshot`, `customer_name_snapshot`, `status`, `remark`, `created_time`, `updated_time`, `deleted`, `deleted_time`, `delivered_at`) VALUES (1,'DEMO-SHP-001',1,1,'DEMO-CUS-001','演示成品客户','POSTED','MES_DEMO:MANUFACTURING_HAPPY_PATH','2026-08-20 23:05:24',NULL,0,NULL,NULL),(222,'DEMO-SOD-SHP-001',225,1,'DEMO-CUS-001','演示成品客户','POSTED','MES_DEMO:SALES_ORDER_DRIVEN_HAPPY_PATH','2026-09-05 21:31:30',NULL,0,NULL,NULL);
/*!40000 ALTER TABLE `erp_shipment` ENABLE KEYS */;

/*!40000 ALTER TABLE `erp_shipment_line` DISABLE KEYS */;
INSERT INTO `erp_shipment_line` (`id`, `shipment_id`, `sales_order_line_id`, `line_no`, `material_id`, `warehouse_id`, `location_id`, `quantity`, `stock_transaction_id`, `lot_id`, `lot_no_snapshot`, `created_time`, `updated_time`, `deleted`, `deleted_time`) VALUES (1,1,1,1,14,3,3,10.000000,4,2,'DEMO-FG-LOT-001','2026-08-20 23:05:24',NULL,0,NULL),(224,222,225,1,458,3,3,10.000000,1039,469,'DEMO-SOD-FG-LOT-001','2026-09-05 21:31:30',NULL,0,NULL);
/*!40000 ALTER TABLE `erp_shipment_line` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
