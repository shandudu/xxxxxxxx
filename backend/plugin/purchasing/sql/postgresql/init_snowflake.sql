insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values (1860000000000000201, 'purchasing.menu', 'ErpPurchasing', '/erp/purchasing', 17, 'mdi:cart-outline', 1, '/plugins/purchasing/views/index', 'erp:purchasing:view', 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null);
insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
(1860000000000000202, '采购订单新建', 'ErpPurchasingCreate', null, 0, null, 2, null, 'erp:purchasing:create', 1, 0, 1, '', null, 1860000000000000201, now(), null),
(1860000000000000203, '采购订单确认', 'ErpPurchasingConfirm', null, 0, null, 2, null, 'erp:purchasing:confirm', 1, 0, 1, '', null, 1860000000000000201, now(), null),
(1860000000000000204, '采购订单取消', 'ErpPurchasingCancel', null, 0, null, 2, null, 'erp:purchasing:cancel', 1, 0, 1, '', null, 1860000000000000201, now(), null),
(1860000000000000205, '供应商收货', 'ErpPurchasingReceipt', null, 0, null, 2, null, 'erp:purchasing:receipt', 1, 0, 1, '', null, 1860000000000000201, now(), null);
