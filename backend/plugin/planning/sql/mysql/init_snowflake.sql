set @planning_parent_id = coalesce(
    (select id from sys_menu where name = 'Mes' and deleted = 0 limit 1),
    (select id from sys_menu where name = 'System' and deleted = 0 limit 1)
);
insert into sys_menu
    (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark,
     parent_id, created_time, updated_time, deleted, deleted_time)
values
    ('planning.menu', 'MesPlanning', '/mes/planning', 17, 'mdi:clipboard-text-clock-outline', 1,
     '/plugins/planning/views/index', 'mes:planning:view', 1, 1, 1, '', null,
     @planning_parent_id, now(), null, 0, null);
set @planning_menu_id = last_insert_id();
insert into sys_menu
    (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark,
     parent_id, created_time, updated_time, deleted, deleted_time)
values
    ('创建主生产计划', 'MesPlanningCreate', null, 0, null, 2, null, 'mes:planning:create', 1, 0, 1, '', null, @planning_menu_id, now(), null, 0, null),
    ('确认主生产计划', 'MesPlanningConfirm', null, 0, null, 2, null, 'mes:planning:confirm', 1, 0, 1, '', null, @planning_menu_id, now(), null, 0, null),
    ('运行物料需求计划', 'MesPlanningRun', null, 0, null, 2, null, 'mes:planning:run', 1, 0, 1, '', null, @planning_menu_id, now(), null, 0, null),
    ('固定计划订单', 'MesPlanningFirm', null, 0, null, 2, null, 'mes:planning:firm', 1, 0, 1, '', null, @planning_menu_id, now(), null, 0, null),
    ('下达计划订单', 'MesPlanningRelease', null, 0, null, 2, null, 'mes:planning:release', 1, 0, 1, '', null, @planning_menu_id, now(), null, 0, null);
