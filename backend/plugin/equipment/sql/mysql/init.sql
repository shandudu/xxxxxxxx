set @system_menu_id = (select id from sys_menu where name = 'System');

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('equipment.menu', 'MesEquipment', '/mes/equipment', 16, 'mdi:robot-industrial', 1, '/plugins/equipment/views/index', null, 1, 1, 1, '', null, @system_menu_id, now(), null);

set @equipment_menu_id = LAST_INSERT_ID();

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('设备配置', 'MesEquipmentConfig', null, 0, null, 2, null, 'mes:equipment:config', 1, 0, 1, '', null, @equipment_menu_id, now(), null),
('设备启停', 'MesEquipmentEnabled', null, 0, null, 2, null, 'mes:equipment:enabled', 1, 0, 1, '', null, @equipment_menu_id, now(), null),
('设备状态', 'MesEquipmentStatus', null, 0, null, 2, null, 'mes:equipment:status', 1, 0, 1, '', null, @equipment_menu_id, now(), null),
('设备分类', 'MesEquipmentCategory', null, 0, null, 2, null, 'mes:equipment:category', 1, 0, 1, '', null, @equipment_menu_id, now(), null);

insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values ('模具全生命周期', 'MesMoldLifecycle', '/mes/equipment/molds', 24, 'mdi:tools', 1, '/plugins/equipment/views/molds', 'mes:equipment:mold:view', 1, 1, 1, '', null, @system_menu_id, now(), null);

set @mold_menu_id = LAST_INSERT_ID();
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
('模具台账配置', 'MesMoldConfig', null, 0, null, 2, null, 'mes:equipment:mold:config', 1, 0, 1, '', null, @mold_menu_id, now(), null),
('模具上下模', 'MesMoldMount', null, 0, null, 2, null, 'mes:equipment:mold:mount', 1, 0, 1, '', null, @mold_menu_id, now(), null),
('模具保养维修', 'MesMoldMaintenance', null, 0, null, 2, null, 'mes:equipment:mold:maintenance', 1, 0, 1, '', null, @mold_menu_id, now(), null),
('模具穴位质量', 'MesMoldQuality', null, 0, null, 2, null, 'mes:equipment:mold:quality', 1, 0, 1, '', null, @mold_menu_id, now(), null);

insert into mes_equipment_category (category_code, category_name, parent_id, status, sort_no, remark, created_time, updated_time)
values
('PRODUCTION', '生产设备', null, 'ACTIVE', 10, null, now(), null),
('INSPECTION', '检测设备', null, 'ACTIVE', 20, null, now(), null),
('LOGISTICS', '物流设备', null, 'ACTIVE', 30, null, now(), null),
('UTILITY', '公辅设备', null, 'ACTIVE', 40, null, now(), null),
('TOOL', '工装设备', null, 'ACTIVE', 50, null, now(), null);
