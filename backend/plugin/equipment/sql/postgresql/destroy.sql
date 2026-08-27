delete from sys_menu where name in ('MesEquipmentConfig', 'MesEquipmentEnabled', 'MesEquipmentStatus', 'MesEquipmentCategory');
delete from sys_menu where name = 'MesEquipment';
drop table if exists mes_equipment;
drop table if exists mes_equipment_category;
select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
