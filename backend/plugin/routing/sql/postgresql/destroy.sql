delete from sys_menu where name in (
    'MesOperationConfig', 'MesOperationStatus', 'MesWorkCenterConfig', 'MesWorkCenterStatus',
    'MesRoutingConfig', 'MesRoutingValidate', 'MesRoutingActivate', 'MesRoutingDeactivate', 'MesRoutingCopy'
);
delete from sys_menu where name in ('MesOperation', 'MesWorkCenter', 'MesRouting');
drop table if exists mes_routing_operation;
drop table if exists mes_routing;
drop table if exists mes_operation;
drop table if exists mes_work_center;
