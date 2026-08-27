delete from sys_role_menu where menu_id in (select id from sys_menu where name = 'MesMaintenance' or parent_id in (select id from sys_menu where name = 'MesMaintenance'));
delete from sys_menu where parent_id in (select id from sys_menu where name = 'MesMaintenance');
delete from sys_menu where name = 'MesMaintenance';
drop table if exists mes_maintenance_task;
drop table if exists mes_repair_order;
drop table if exists mes_equipment_downtime;
drop table if exists mes_maintenance_plan;
