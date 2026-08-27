set @system_menu_id = (select id from sys_menu where name = 'System');
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('purchasing.menu', 'ErpPurchasing', '/erp/purchasing', 17, 'mdi:cart-outline', 1, '/plugins/purchasing/views/index', 'erp:purchasing:view', 1, 1, 1, '', null, @system_menu_id, now(), null);
set @purchasing_menu_id = LAST_INSERT_ID();
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('采购订单新建', 'ErpPurchasingCreate', null, 0, null, 2, null, 'erp:purchasing:create', 1, 0, 1, '', null, @purchasing_menu_id, now(), null),
('采购订单确认', 'ErpPurchasingConfirm', null, 0, null, 2, null, 'erp:purchasing:confirm', 1, 0, 1, '', null, @purchasing_menu_id, now(), null),
('采购订单取消', 'ErpPurchasingCancel', null, 0, null, 2, null, 'erp:purchasing:cancel', 1, 0, 1, '', null, @purchasing_menu_id, now(), null),
('供应商收货', 'ErpPurchasingReceipt', null, 0, null, 2, null, 'erp:purchasing:receipt', 1, 0, 1, '', null, @purchasing_menu_id, now(), null);
