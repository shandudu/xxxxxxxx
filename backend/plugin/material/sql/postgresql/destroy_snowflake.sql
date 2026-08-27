delete from sys_menu where name in ('MesMaterialConfig', 'MesMaterialStatus', 'MesMaterialCategory', 'MesMaterialUnit');
delete from sys_menu where name = 'MesMaterial';
drop table if exists mes_material;
drop table if exists mes_material_category;
drop table if exists mes_unit;
