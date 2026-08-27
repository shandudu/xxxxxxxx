delete from sys_menu where name in ('ErpSupplierView', 'ErpSupplierConfig', 'ErpSupplierStatus', 'ErpSupplierCooperation', 'ErpSupplierQuality', 'ErpSupplierCategory', 'ErpSupplierContact', 'ErpSupplierMaterial');
delete from sys_menu where name = 'ErpSupplier';
drop table if exists erp_supplier_operation_log;
drop table if exists erp_supplier_material;
drop table if exists erp_supplier_contact;
drop table if exists erp_supplier;
drop table if exists erp_supplier_category;
