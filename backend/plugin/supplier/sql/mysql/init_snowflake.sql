set @system_menu_id = (select id from sys_menu where name = 'System');

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('supplier.menu', 'ErpSupplier', '/erp/supplier', 21, 'mdi:truck-delivery-outline', 1, '/plugins/supplier/views/index', null, 1, 1, 1, '', null, @system_menu_id, now(), null);

set @supplier_menu_id = LAST_INSERT_ID();

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('供应商查看', 'ErpSupplierView', null, 0, null, 2, null, 'erp:supplier:view', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('供应商配置', 'ErpSupplierConfig', null, 0, null, 2, null, 'erp:supplier:config', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('供应商状态', 'ErpSupplierStatus', null, 0, null, 2, null, 'erp:supplier:status', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('合作状态', 'ErpSupplierCooperation', null, 0, null, 2, null, 'erp:supplier:cooperation', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('质量状态', 'ErpSupplierQuality', null, 0, null, 2, null, 'erp:supplier:quality', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('供应商分类', 'ErpSupplierCategory', null, 0, null, 2, null, 'erp:supplier:category', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('联系人管理', 'ErpSupplierContact', null, 0, null, 2, null, 'erp:supplier:contact', 1, 0, 1, '', null, @supplier_menu_id, now(), null),
('供货物料管理', 'ErpSupplierMaterial', null, 0, null, 2, null, 'erp:supplier:material', 1, 0, 1, '', null, @supplier_menu_id, now(), null);
