do $$
declare customer_menu_id bigint;
begin
  insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
  values ('customer.menu', 'ErpCustomer', '/erp/customer', 21, 'mdi:account-group', 1, '/plugins/customer/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
  returning id into customer_menu_id;
  insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
  values ('客户配置', 'ErpCustomerConfig', null, 0, null, 2, null, 'mes:customer:config', 1, 0, 1, '', null, customer_menu_id, now(), null), ('客户状态', 'ErpCustomerStatus', null, 0, null, 2, null, 'mes:customer:status', 1, 0, 1, '', null, customer_menu_id, now(), null), ('客户分类', 'ErpCustomerCategory', null, 0, null, 2, null, 'mes:customer:category', 1, 0, 1, '', null, customer_menu_id, now(), null), ('客户联系人', 'ErpCustomerContact', null, 0, null, 2, null, 'mes:customer:contact', 1, 0, 1, '', null, customer_menu_id, now(), null), ('客户地址', 'ErpCustomerAddress', null, 0, null, 2, null, 'mes:customer:address', 1, 0, 1, '', null, customer_menu_id, now(), null);
end $$;
