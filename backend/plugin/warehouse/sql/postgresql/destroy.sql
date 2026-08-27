delete from sys_menu where name in ('MesWarehouseConfig', 'MesWarehouseStatus', 'MesLocationConfig', 'MesLocationStatus', 'MesLocationGenerate');
delete from sys_menu where name = 'MesWarehouse';
drop table if exists mes_location;
drop table if exists mes_area;
drop table if exists mes_warehouse;
select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;

