set @system_menu_id=(select id from sys_menu where name='System');
insert into sys_menu (title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values ('quality.menu','MesQuality','/mes/quality',19,'mdi:shield-check-outline',1,'/plugins/quality/views/index','mes:quality:view',1,1,1,'',null,@system_menu_id,now(),null);
set @quality_menu_id=LAST_INSERT_ID();
insert into sys_menu (title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values
('质量检验','MesQualityInspection',null,0,null,2,null,'mes:quality:inspection',1,0,1,'',null,@quality_menu_id,now(),null),
('不合格报告','MesQualityNcr',null,0,null,2,null,'mes:quality:ncr',1,0,1,'',null,@quality_menu_id,now(),null),
('MRB 处置','MesQualityMrb',null,0,null,2,null,'mes:quality:mrb',1,0,1,'',null,@quality_menu_id,now(),null),
('处置执行','MesQualityMrbExecute',null,0,null,2,null,'mes:quality:mrb:execute',1,0,1,'',null,@quality_menu_id,now(),null),
('质量基础配置','MesQualityConfig',null,0,null,2,null,'mes:quality:config',1,0,1,'',null,@quality_menu_id,now(),null);
insert into sys_menu (title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time)
values ('供应商质量管理','MesSupplierQuality','/mes/quality/sqm',20,'mdi:account-hard-hat-outline',1,'/plugins/quality/views/sqm','mes:quality:sqm:view',1,1,1,'',null,@quality_menu_id,now(),null);
set @sqm_menu_id=LAST_INSERT_ID();
insert into sys_menu (title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values
('供应商整改管理','MesSupplierQualityScar',null,0,null,2,null,'mes:quality:sqm:scar',1,0,1,'',null,@sqm_menu_id,now(),null),
('供应商整改验证','MesSupplierQualityVerify',null,0,null,2,null,'mes:quality:sqm:verify',1,0,1,'',null,@sqm_menu_id,now(),null),
('供应商质量策略','MesSupplierQualityPolicy',null,0,null,2,null,'mes:quality:sqm:policy',1,0,1,'',null,@sqm_menu_id,now(),null);
