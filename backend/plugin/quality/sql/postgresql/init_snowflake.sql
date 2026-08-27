insert into sys_menu (id,title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values (1860000000000000401,'quality.menu','MesQuality','/mes/quality',19,'mdi:shield-check-outline',1,'/plugins/quality/views/index','mes:quality:view',1,1,1,'',null,(select id from sys_menu where name='System'),now(),null);
insert into sys_menu (id,title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values
(1860000000000000402,'质量检验','MesQualityInspection',null,0,null,2,null,'mes:quality:inspection',1,0,1,'',null,1860000000000000401,now(),null),
(1860000000000000403,'不合格报告','MesQualityNcr',null,0,null,2,null,'mes:quality:ncr',1,0,1,'',null,1860000000000000401,now(),null),
(1860000000000000404,'MRB 处置','MesQualityMrb',null,0,null,2,null,'mes:quality:mrb',1,0,1,'',null,1860000000000000401,now(),null),
(1860000000000000405,'处置执行','MesQualityMrbExecute',null,0,null,2,null,'mes:quality:mrb:execute',1,0,1,'',null,1860000000000000401,now(),null),
(1860000000000000406,'质量基础配置','MesQualityConfig',null,0,null,2,null,'mes:quality:config',1,0,1,'',null,1860000000000000401,now(),null);
