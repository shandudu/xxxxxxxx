set @system_menu_id = (select id from sys_menu where name = 'System');

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('customer.menu', 'ErpCustomer', '/erp/customer', 21, 'mdi:account-group', 1, '/plugins/customer/views/index', null, 1, 1, 1, '', null, @system_menu_id, now(), null);

set @customer_menu_id = LAST_INSERT_ID();
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('客户配置', 'ErpCustomerConfig', null, 0, null, 2, null, 'mes:customer:config', 1, 0, 1, '', null, @customer_menu_id, now(), null),
('客户状态', 'ErpCustomerStatus', null, 0, null, 2, null, 'mes:customer:status', 1, 0, 1, '', null, @customer_menu_id, now(), null),
('客户分类', 'ErpCustomerCategory', null, 0, null, 2, null, 'mes:customer:category', 1, 0, 1, '', null, @customer_menu_id, now(), null),
('客户联系人', 'ErpCustomerContact', null, 0, null, 2, null, 'mes:customer:contact', 1, 0, 1, '', null, @customer_menu_id, now(), null),
('客户地址', 'ErpCustomerAddress', null, 0, null, 2, null, 'mes:customer:address', 1, 0, 1, '', null, @customer_menu_id, now(), null);

insert into erp_customer_category (category_code, category_name, parent_id, status, sort_no, remark, created_time, updated_time)
values ('DOMESTIC', '国内客户', null, 'ACTIVE', 10, null, now(), null), ('OVERSEAS', '海外客户', null, 'ACTIVE', 20, null, now(), null), ('DISTRIBUTOR', '经销商', null, 'ACTIVE', 30, null, now(), null), ('INTERNAL', '内部客户', null, 'ACTIVE', 40, null, now(), null);
