set @costing_parent_id = coalesce((select id from sys_menu where name = 'ERP' and deleted = 0 limit 1), (select id from sys_menu where name = 'System' and deleted = 0 limit 1));
insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values (1860000000000001001, '生产成本与毛利', 'ErpCosting', '/erp/costing', 90, 'mdi:finance', 1, '/plugins/costing/views/index', 'erp:costing:view', 1, 1, 1, '', '生产成本核算、工单结转、产品/客户毛利', @costing_parent_id, now(), null, 0, null);
insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
(1860000000000001002, '成本期间维护', 'ErpCostingManage', null, 0, null, 2, null, 'erp:costing:manage', 1, 0, 1, '', null, 1860000000000001001, now(), null, 0, null),
(1860000000000001003, '工单成本计算', 'ErpCostingCalculate', null, 0, null, 2, null, 'erp:costing:calculate', 1, 0, 1, '', null, 1860000000000001001, now(), null, 0, null),
(1860000000000001004, '工单成本结转', 'ErpCostingPost', null, 0, null, 2, null, 'erp:costing:post', 1, 0, 1, '', null, 1860000000000001001, now(), null, 0, null),
(1860000000000001005, '关闭成本期间', 'ErpCostingClose', null, 0, null, 2, null, 'erp:costing:close', 1, 0, 1, '', null, 1860000000000001001, now(), null, 0, null);
