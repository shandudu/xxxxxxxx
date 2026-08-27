do $$
declare
    operation_menu_id bigint;
    work_center_menu_id bigint;
    routing_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('routing.operationMenu', 'MesOperation', '/mes/operation', 13, 'mdi:format-list-numbered', 1, '/plugins/routing/views/operation', 'mes:operation:view', 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into operation_menu_id;
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('routing.workCenterMenu', 'MesWorkCenter', '/mes/work-center', 14, 'mdi:factory', 1, '/plugins/routing/views/work-center', 'mes:workcenter:view', 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into work_center_menu_id;
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('routing.menu', 'MesRouting', '/mes/routing', 15, 'mdi:source-branch', 1, '/plugins/routing/views/routing', 'mes:routing:view', 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into routing_menu_id;
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('工序配置', 'MesOperationConfig', null, 0, null, 2, null, 'mes:operation:config', 1, 0, 1, '', null, operation_menu_id, now(), null),
    ('工序状态', 'MesOperationStatus', null, 0, null, 2, null, 'mes:operation:status', 1, 0, 1, '', null, operation_menu_id, now(), null),
    ('工作中心配置', 'MesWorkCenterConfig', null, 0, null, 2, null, 'mes:workcenter:config', 1, 0, 1, '', null, work_center_menu_id, now(), null),
    ('工作中心状态', 'MesWorkCenterStatus', null, 0, null, 2, null, 'mes:workcenter:status', 1, 0, 1, '', null, work_center_menu_id, now(), null),
    ('工艺路线配置', 'MesRoutingConfig', null, 0, null, 2, null, 'mes:routing:config', 1, 0, 1, '', null, routing_menu_id, now(), null),
    ('工艺路线校验', 'MesRoutingValidate', null, 0, null, 2, null, 'mes:routing:validate', 1, 0, 1, '', null, routing_menu_id, now(), null),
    ('工艺路线生效', 'MesRoutingActivate', null, 0, null, 2, null, 'mes:routing:activate', 1, 0, 1, '', null, routing_menu_id, now(), null),
    ('工艺路线停用', 'MesRoutingDeactivate', null, 0, null, 2, null, 'mes:routing:deactivate', 1, 0, 1, '', null, routing_menu_id, now(), null),
    ('复制工艺路线', 'MesRoutingCopy', null, 0, null, 2, null, 'mes:routing:copy', 1, 0, 1, '', null, routing_menu_id, now(), null);
end $$;
