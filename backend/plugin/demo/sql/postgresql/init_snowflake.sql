do $$
declare parent_id bigint; menu_id bigint;
begin
select id into parent_id from sys_menu where name = 'Mes' and deleted = 0 limit 1;
if parent_id is null then select id into parent_id from sys_menu where name = 'System' and deleted = 0 limit 1; end if;
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('demo.menu', 'MesDemoCenter', '/mes/demo-center', 30, 'mdi:flask-outline', 1, '/plugins/demo/views/index', 'mes:demo:view', 1, 1, 1, '', null, parent_id, now(), null, 0, null) returning id into menu_id;
insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values ('运行制造闭环演示', 'MesDemoRun', null, 0, null, 2, null, 'mes:demo:run', 1, 0, 1, '', null, menu_id, now(), null, 0, null);
end $$;
