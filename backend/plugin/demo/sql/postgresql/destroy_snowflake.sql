do $$
declare menu_id bigint;
begin
select id into menu_id from sys_menu where name = 'MesDemoCenter' limit 1;
if menu_id is not null then
  delete from sys_role_menu where menu_id in (select id from sys_menu where parent_id = menu_id) or menu_id = menu_id;
  delete from sys_menu where parent_id = menu_id;
  delete from sys_menu where id = menu_id;
end if;
end $$;
drop table if exists mes_demo_run;
