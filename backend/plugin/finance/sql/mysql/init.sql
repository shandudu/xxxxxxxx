set @finance_parent_id = coalesce((select id from sys_menu where name = 'ERP' and deleted = 0 limit 1), (select id from sys_menu where name = 'System' and deleted = 0 limit 1));
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('财务经营', 'ErpFinance', '/erp/finance', 95, 'mdi:finance', 1, '/plugins/finance/views/index', 'erp:finance:view', 1, 1, 1, '', '库存计价、应收应付、财务凭证与利润驾驶舱', @finance_parent_id, now(), null, 0, null);
set @finance_menu_id = last_insert_id();
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
('财务期间维护', 'ErpFinanceManage', null, 0, null, 2, null, 'erp:finance:manage', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('库存计价', 'ErpFinanceValuate', null, 0, null, 2, null, 'erp:finance:valuate', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('应收管理', 'ErpFinanceAR', null, 0, null, 2, null, 'erp:finance:ar', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('应付管理', 'ErpFinanceAP', null, 0, null, 2, null, 'erp:finance:ap', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('凭证生成', 'ErpFinanceVoucher', null, 0, null, 2, null, 'erp:finance:voucher', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null);
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('银行对账', 'ErpFinanceBank', null, 0, null, 2, null, 'erp:finance:bank', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null);
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
('月结关账', 'ErpFinanceClose', null, 0, null, 2, null, 'erp:finance:close', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('库存盘点', 'ErpFinanceCount', null, 0, null, 2, null, 'erp:finance:count', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('税务台账', 'ErpFinanceTax', null, 0, null, 2, null, 'erp:finance:tax', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('现金流预测', 'ErpFinanceCashflow', null, 0, null, 2, null, 'erp:finance:cashflow', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null);
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
('预算与成本中心', 'ErpFinanceBudget', null, 0, null, 2, null, 'erp:finance:budget', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null),
('费用报销', 'ErpFinanceExpense', null, 0, null, 2, null, 'erp:finance:expense', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null);
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('固定资产', 'ErpFinanceAsset', null, 0, null, 2, null, 'erp:finance:asset', 1, 0, 1, '', null, @finance_menu_id, now(), null, 0, null);
