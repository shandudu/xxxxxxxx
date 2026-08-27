do $$
declare maintenance_parent_id bigint;
declare maintenance_menu_id bigint;
begin
select id into maintenance_parent_id from sys_menu where name = 'Mes' and deleted = 0 limit 1;
if maintenance_parent_id is null then select id into maintenance_parent_id from sys_menu where name = 'System' and deleted = 0 limit 1; end if;
select coalesce(max(id), 0) + 1 into maintenance_menu_id from sys_menu;
insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
(maintenance_menu_id, 'maintenance.menu', 'MesMaintenance', '/mes/maintenance', 19, 'mdi:tools', 1, '/plugins/maintenance/views/index', 'mes:maintenance:view', 1, 1, 1, '', null, maintenance_parent_id, now(), null, 0, null),
(maintenance_menu_id + 1, '配置运维计划', 'MesMaintenanceConfig', null, 0, null, 2, null, 'mes:maintenance:config', 1, 0, 1, '', null, maintenance_menu_id, now(), null, 0, null),
(maintenance_menu_id + 2, '生成运维任务', 'MesMaintenanceGenerate', null, 0, null, 2, null, 'mes:maintenance:generate', 1, 0, 1, '', null, maintenance_menu_id, now(), null, 0, null),
(maintenance_menu_id + 3, '执行点检保养', 'MesMaintenanceExecute', null, 0, null, 2, null, 'mes:maintenance:execute', 1, 0, 1, '', null, maintenance_menu_id, now(), null, 0, null),
(maintenance_menu_id + 4, '设备维修', 'MesMaintenanceRepair', null, 0, null, 2, null, 'mes:maintenance:repair', 1, 0, 1, '', null, maintenance_menu_id, now(), null, 0, null),
(maintenance_menu_id + 5, '停机管理', 'MesMaintenanceDowntime', null, 0, null, 2, null, 'mes:maintenance:downtime', 1, 0, 1, '', null, maintenance_menu_id, now(), null, 0, null);
end $$;
