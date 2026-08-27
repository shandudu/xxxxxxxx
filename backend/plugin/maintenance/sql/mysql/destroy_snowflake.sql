set @maintenance_menu_id = (select id from sys_menu where name = 'MesMaintenance' limit 1);
delete from sys_role_menu where menu_id in (select id from sys_menu where parent_id = @maintenance_menu_id) or menu_id = @maintenance_menu_id;
delete from sys_menu where parent_id = @maintenance_menu_id;
delete from sys_menu where id = @maintenance_menu_id;
drop table if exists mes_maintenance_task;
drop table if exists mes_repair_order;
drop table if exists mes_equipment_downtime;
drop table if exists mes_maintenance_plan;
