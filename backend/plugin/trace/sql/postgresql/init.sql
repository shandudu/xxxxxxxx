do $$
declare
    trace_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('trace.menu', 'MesTrace', '/mes/trace', 15, 'mdi:graph-outline', 1, '/plugins/trace/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into trace_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('Trace view', 'MesTraceView', null, 0, null, 2, null, 'mes:trace:view', 1, 0, 1, '', null, trace_menu_id, now(), null),
    ('Trace rule config', 'MesTraceRuleConfig', null, 0, null, 2, null, 'mes:trace:rule:config', 1, 0, 1, '', null, trace_menu_id, now(), null),
    ('Lot config', 'MesTraceLotConfig', null, 0, null, 2, null, 'mes:trace:lot:config', 1, 0, 1, '', null, trace_menu_id, now(), null),
    ('Serial generate', 'MesTraceSerialGenerate', null, 0, null, 2, null, 'mes:trace:serial:generate', 1, 0, 1, '', null, trace_menu_id, now(), null),
    ('Trace relation config', 'MesTraceRelationConfig', null, 0, null, 2, null, 'mes:trace:relation:config', 1, 0, 1, '', null, trace_menu_id, now(), null),
    ('Trace query', 'MesTraceQuery', null, 0, null, 2, null, 'mes:trace:query', 1, 0, 1, '', null, trace_menu_id, now(), null);
end $$;

