do $$
declare performance_parent_id bigint;
declare performance_menu_id bigint;
begin
select id into performance_parent_id from sys_menu where name = 'Mes' and deleted = 0 limit 1;
if performance_parent_id is null then select id into performance_parent_id from sys_menu where name = 'System' and deleted = 0 limit 1; end if;
select coalesce(max(id), 0) + 1 into performance_menu_id from sys_menu;
insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time, deleted, deleted_time)
values
(performance_menu_id, 'performance.menu', 'MesPerformance', '/mes/performance', 20, 'mdi:chart-box-outline', 1, '/plugins/performance/views/index', 'mes:performance:view', 1, 1, 1, '', null, performance_parent_id, now(), null, 0, null),
(performance_menu_id + 1, '配置绩效目标', 'MesPerformanceTarget', null, 0, null, 2, null, 'mes:performance:target', 1, 0, 1, '', null, performance_menu_id, now(), null, 0, null),
(performance_menu_id + 2, '重建绩效快照', 'MesPerformanceRebuild', null, 0, null, 2, null, 'mes:performance:rebuild', 1, 0, 1, '', null, performance_menu_id, now(), null, 0, null);
end $$;
