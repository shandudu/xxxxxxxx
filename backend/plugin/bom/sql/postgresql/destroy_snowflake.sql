delete from sys_menu where name in ('MesBomConfig', 'MesBomValidate', 'MesBomActivate', 'MesBomDeactivate', 'MesBomCopy');
delete from sys_menu where name = 'MesBom';
drop table if exists mes_bom_item;
drop table if exists mes_bom;
