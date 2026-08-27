do $$
declare
    equipment_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('equipment.menu', 'MesEquipment', '/mes/equipment', 16, 'mdi:robot-industrial', 1, '/plugins/equipment/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into equipment_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('设备配置', 'MesEquipmentConfig', null, 0, null, 2, null, 'mes:equipment:config', 1, 0, 1, '', null, equipment_menu_id, now(), null),
    ('设备启停', 'MesEquipmentEnabled', null, 0, null, 2, null, 'mes:equipment:enabled', 1, 0, 1, '', null, equipment_menu_id, now(), null),
    ('设备状态', 'MesEquipmentStatus', null, 0, null, 2, null, 'mes:equipment:status', 1, 0, 1, '', null, equipment_menu_id, now(), null),
    ('设备分类', 'MesEquipmentCategory', null, 0, null, 2, null, 'mes:equipment:category', 1, 0, 1, '', null, equipment_menu_id, now(), null);
end $$;

insert into mes_equipment_category (category_code, category_name, parent_id, status, sort_no, remark, created_time, updated_time)
values
('PRODUCTION', '生产设备', null, 'ACTIVE', 10, null, now(), null),
('INSPECTION', '检测设备', null, 'ACTIVE', 20, null, now(), null),
('LOGISTICS', '物流设备', null, 'ACTIVE', 30, null, now(), null),
('UTILITY', '公辅设备', null, 'ACTIVE', 40, null, now(), null),
('TOOL', '工装设备', null, 'ACTIVE', 50, null, now(), null);
