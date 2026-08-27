set @scheduling_parent_id = coalesce(
    (select id from sys_menu where name = 'Mes' and deleted = 0 limit 1),
    (select id from sys_menu where name = 'System' and deleted = 0 limit 1)
);
set @scheduling_menu_id = (select coalesce(max(id), 0) + 1 from sys_menu);
insert into sys_menu
    (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark,
     parent_id, created_time, updated_time, deleted, deleted_time)
values
    (@scheduling_menu_id, 'scheduling.menu', 'MesScheduling', '/mes/scheduling', 18, 'mdi:chart-timeline-variant-shimmer', 1,
     '/plugins/scheduling/views/index', 'mes:scheduling:view', 1, 1, 1, '', null,
     @scheduling_parent_id, now(), null, 0, null);
insert into sys_menu
    (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark,
     parent_id, created_time, updated_time, deleted, deleted_time)
values
    (@scheduling_menu_id + 1, '配置班次与日历', 'MesSchedulingConfig', null, 0, null, 2, null, 'mes:scheduling:config', 1, 0, 1, '', null, @scheduling_menu_id, now(), null, 0, null),
    (@scheduling_menu_id + 2, '运行有限产能排程', 'MesSchedulingRun', null, 0, null, 2, null, 'mes:scheduling:run', 1, 0, 1, '', null, @scheduling_menu_id, now(), null, 0, null),
    (@scheduling_menu_id + 3, '发布排程', 'MesSchedulingPublish', null, 0, null, 2, null, 'mes:scheduling:publish', 1, 0, 1, '', null, @scheduling_menu_id, now(), null, 0, null),
    (@scheduling_menu_id + 4, '工序派工', 'MesSchedulingDispatch', null, 0, null, 2, null, 'mes:scheduling:dispatch', 1, 0, 1, '', null, @scheduling_menu_id, now(), null, 0, null);

set @shopfloor_menu_id = @scheduling_menu_id + 5;
insert into sys_menu
    (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark,
     parent_id, created_time, updated_time, deleted, deleted_time)
values
    (@shopfloor_menu_id, 'shopfloor.menu', 'MesShopfloor', '/mes/shopfloor', 19, 'mdi:monitor-dashboard', 1,
     '/plugins/shopfloor/views/index', 'mes:shopfloor:view', 1, 1, 1, '', null, @scheduling_parent_id, now(), null, 0, null),
    (@shopfloor_menu_id + 1, '维护生产班组', 'MesShopfloorTeam', null, 0, null, 2, null, 'mes:shopfloor:team', 1, 0, 1, '', null, @shopfloor_menu_id, now(), null, 0, null),
    (@shopfloor_menu_id + 2, '维护生产工位', 'MesShopfloorWorkstation', null, 0, null, 2, null, 'mes:shopfloor:workstation', 1, 0, 1, '', null, @shopfloor_menu_id, now(), null, 0, null),
    (@shopfloor_menu_id + 3, '操作工位终端', 'MesShopfloorOperate', null, 0, null, 2, null, 'mes:shopfloor:operate', 1, 0, 1, '', null, @shopfloor_menu_id, now(), null, 0, null);
