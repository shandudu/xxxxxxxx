set @planning_menu_id = (select id from sys_menu where name = 'MesPlanning' limit 1);
delete from sys_menu where parent_id = @planning_menu_id;
delete from sys_menu where id = @planning_menu_id;
drop table if exists mes_planned_order;
drop table if exists mes_mrp_requirement;
drop table if exists mes_mrp_run;
drop table if exists mes_mps_demand;
drop table if exists mes_mps_plan;
