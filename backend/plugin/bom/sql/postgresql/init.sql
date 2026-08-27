do $$
declare
    bom_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('bom.menu', 'MesBom', '/mes/bom', 12, 'mdi:file-tree', 1, '/plugins/bom/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into bom_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('BOM配置', 'MesBomConfig', null, 0, null, 2, null, 'mes:bom:config', 1, 0, 1, '', null, bom_menu_id, now(), null),
    ('BOM校验', 'MesBomValidate', null, 0, null, 2, null, 'mes:bom:validate', 1, 0, 1, '', null, bom_menu_id, now(), null),
    ('BOM生效', 'MesBomActivate', null, 0, null, 2, null, 'mes:bom:activate', 1, 0, 1, '', null, bom_menu_id, now(), null),
    ('BOM停用', 'MesBomDeactivate', null, 0, null, 2, null, 'mes:bom:deactivate', 1, 0, 1, '', null, bom_menu_id, now(), null),
    ('BOM复制', 'MesBomCopy', null, 0, null, 2, null, 'mes:bom:copy', 1, 0, 1, '', null, bom_menu_id, now(), null);
end $$;
