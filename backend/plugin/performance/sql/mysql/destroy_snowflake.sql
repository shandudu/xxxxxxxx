set @performance_menu_id = (select id from sys_menu where name = 'MesPerformance' limit 1);
delete from sys_role_menu where menu_id in (select id from sys_menu where parent_id = @performance_menu_id) or menu_id = @performance_menu_id;
delete from sys_menu where parent_id = @performance_menu_id;
delete from sys_menu where id = @performance_menu_id;
drop table if exists mes_performance_snapshot;
drop table if exists mes_performance_target;
