set @demo_parent_id = coalesce((select id from sys_menu where name = 'Mes' and deleted = 0 limit 1), (select id from sys_menu where name = 'System' and deleted = 0 limit 1));
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('demo.menu', 'MesDemoCenter', '/mes/demo-center', 30, 'mdi:flask-outline', 1, '/plugins/demo/views/index', 'mes:demo:view', 1, 1, 1, '', null, @demo_parent_id, now(), null, 0, null);
set @demo_menu_id = last_insert_id();
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('运行制造闭环演示', 'MesDemoRun', null, 0, null, 2, null, 'mes:demo:run', 1, 0, 1, '', null, @demo_menu_id, now(), null, 0, null);
