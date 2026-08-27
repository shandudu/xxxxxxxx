do $$
declare
    warehouse_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('warehouse.menu', 'MesWarehouse', '/mes/warehouse', 10, 'mdi:warehouse', 1, '/plugins/warehouse/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into warehouse_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('仓库配置', 'MesWarehouseConfig', null, 0, null, 2, null, 'mes:warehouse:config', 1, 0, 1, '', null, warehouse_menu_id, now(), null),
    ('仓库状态', 'MesWarehouseStatus', null, 0, null, 2, null, 'mes:warehouse:status', 1, 0, 1, '', null, warehouse_menu_id, now(), null),
    ('库位配置', 'MesLocationConfig', null, 0, null, 2, null, 'mes:location:config', 1, 0, 1, '', null, warehouse_menu_id, now(), null),
    ('库位状态', 'MesLocationStatus', null, 0, null, 2, null, 'mes:location:status', 1, 0, 1, '', null, warehouse_menu_id, now(), null),
    ('批量生成库位', 'MesLocationGenerate', null, 0, null, 2, null, 'mes:location:generate', 1, 0, 1, '', null, warehouse_menu_id, now(), null);
end $$;
