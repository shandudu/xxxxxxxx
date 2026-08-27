delete from sys_menu where name in ('MesEquipmentConfig', 'MesEquipmentEnabled', 'MesEquipmentStatus', 'MesEquipmentCategory');
delete from sys_menu where name = 'MesEquipment';
drop table if exists mes_equipment;
drop table if exists mes_equipment_category;
