insert into sys_menu (id,title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values (1860000000000000301,'production.menu','MesProduction','/mes/production',18,'mdi:factory',1,'/plugins/production/views/index','mes:production:view',1,1,1,'',null,(select id from sys_menu where name='System'),now(),null);
insert into sys_menu (id,title,name,path,sort,icon,type,component,perms,status,display,cache,link,remark,parent_id,created_time,updated_time) values
(1860000000000000302,'工单创建','MesProductionCreate',null,0,null,2,null,'mes:production:create',1,0,1,'',null,1860000000000000301,now(),null),
(1860000000000000303,'工单下达','MesProductionRelease',null,0,null,2,null,'mes:production:release',1,0,1,'',null,1860000000000000301,now(),null),
(1860000000000000304,'生产执行','MesProductionExecute',null,0,null,2,null,'mes:production:execute',1,0,1,'',null,1860000000000000301,now(),null),
(1860000000000000305,'生产领料','MesProductionIssue',null,0,null,2,null,'mes:production:issue',1,0,1,'',null,1860000000000000301,now(),null),
(1860000000000000306,'生产退料','MesProductionReturn',null,0,null,2,null,'mes:production:return',1,0,1,'',null,1860000000000000301,now(),null),
(1860000000000000307,'生产报工','MesProductionReport',null,0,null,2,null,'mes:production:report',1,0,1,'',null,1860000000000000301,now(),null);
