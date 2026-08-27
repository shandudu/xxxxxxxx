delete from sys_menu where name in ('MesMaterialConfig', 'MesMaterialStatus', 'MesMaterialCategory', 'MesMaterialUnit');
delete from sys_menu where name = 'MesMaterial';
drop table if exists mes_material;
drop table if exists mes_material_category;
drop table if exists mes_unit;
select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
