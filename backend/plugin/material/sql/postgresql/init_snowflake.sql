do $$
declare
    material_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values ('material.menu', 'MesMaterial', '/mes/material', 11, 'mdi:package-variant-closed', 1, '/plugins/material/views/index', null, 1, 1, 1, '', null, (select id from sys_menu where name = 'System'), now(), null)
    returning id into material_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
    values
    ('物料配置', 'MesMaterialConfig', null, 0, null, 2, null, 'mes:material:config', 1, 0, 1, '', null, material_menu_id, now(), null),
    ('物料状态', 'MesMaterialStatus', null, 0, null, 2, null, 'mes:material:status', 1, 0, 1, '', null, material_menu_id, now(), null),
    ('物料分类', 'MesMaterialCategory', null, 0, null, 2, null, 'mes:material:category', 1, 0, 1, '', null, material_menu_id, now(), null),
    ('物料单位', 'MesMaterialUnit', null, 0, null, 2, null, 'mes:material:unit', 1, 0, 1, '', null, material_menu_id, now(), null);
end $$;

insert into mes_unit (id, unit_code, unit_name, symbol, status, decimal_places, remark, created_time, updated_time)
values
(1, 'PCS', '件', 'pcs', 'ACTIVE', 0, null, now(), null),
(2, 'KG', '千克', 'kg', 'ACTIVE', 3, null, now(), null),
(3, 'G', '克', 'g', 'ACTIVE', 3, null, now(), null),
(4, 'T', '吨', 't', 'ACTIVE', 3, null, now(), null),
(5, 'M', '米', 'm', 'ACTIVE', 3, null, now(), null),
(6, 'MM', '毫米', 'mm', 'ACTIVE', 3, null, now(), null),
(7, 'L', '升', 'L', 'ACTIVE', 3, null, now(), null),
(8, 'ML', '毫升', 'ml', 'ACTIVE', 3, null, now(), null),
(9, 'BOX', '箱', 'box', 'ACTIVE', 0, null, now(), null),
(10, 'ROLL', '卷', 'roll', 'ACTIVE', 0, null, now(), null),
(11, 'SET', '套', 'set', 'ACTIVE', 0, null, now(), null);

insert into mes_material_category (id, category_code, category_name, parent_id, status, sort_no, remark, created_time, updated_time)
values
(1, 'RAW', '原材料', null, 'ACTIVE', 10, null, now(), null),
(2, 'SEMI', '半成品', null, 'ACTIVE', 20, null, now(), null),
(3, 'FG', '成品', null, 'ACTIVE', 30, null, now(), null),
(4, 'AUX', '辅料', null, 'ACTIVE', 40, null, now(), null),
(5, 'PACK', '包装材料', null, 'ACTIVE', 50, null, now(), null),
(6, 'SPARE', '备品备件', null, 'ACTIVE', 60, null, now(), null),
(7, 'CONSUMABLE', '耗材', null, 'ACTIVE', 70, null, now(), null);
