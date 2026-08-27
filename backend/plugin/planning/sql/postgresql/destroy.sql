delete from sys_menu where parent_id in (select id from sys_menu where name = 'MesPlanning');
delete from sys_menu where name = 'MesPlanning';
drop table if exists mes_planned_order;
drop table if exists mes_mrp_requirement;
drop table if exists mes_mrp_run;
drop table if exists mes_mps_demand;
drop table if exists mes_mps_plan;
