set @system_menu_id = (select id from sys_menu where name = 'System');

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('inventory.menu', 'MesInventory', '/mes/inventory', 16, 'mdi:clipboard-list-outline', 1, '/plugins/inventory/views/index', null, 1, 1, 1, '', null, @system_menu_id, now(), null);

set @inventory_menu_id = LAST_INSERT_ID();

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('库存调拨新建', 'MesInventoryMovementCreate', null, 0, null, 2, null, 'mes:inventory:movement:create', 1, 0, 1, '', null, @inventory_menu_id, now(), null),
('库存调拨过账', 'MesInventoryMovementPost', null, 0, null, 2, null, 'mes:inventory:movement:post', 1, 0, 1, '', null, @inventory_menu_id, now(), null),
('库存调整', 'MesInventoryAdjustment', null, 0, null, 2, null, 'mes:inventory:adjustment', 1, 0, 1, '', null, @inventory_menu_id, now(), null);
