delete from sys_role_menu where menu_id in (select id from sys_menu where name = 'MesPerformance' or parent_id in (select id from sys_menu where name = 'MesPerformance'));
delete from sys_menu where parent_id in (select id from sys_menu where name = 'MesPerformance');
delete from sys_menu where name = 'MesPerformance';
drop table if exists mes_performance_snapshot;
drop table if exists mes_performance_target;
