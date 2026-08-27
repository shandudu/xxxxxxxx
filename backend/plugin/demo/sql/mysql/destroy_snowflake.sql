set @demo_menu_id = (select id from sys_menu where name = 'MesDemoCenter' limit 1);
delete from sys_role_menu where menu_id in (select id from sys_menu where parent_id = @demo_menu_id) or menu_id = @demo_menu_id;
delete from sys_menu where parent_id = @demo_menu_id;
delete from sys_menu where id = @demo_menu_id;
drop table if exists mes_demo_run;
