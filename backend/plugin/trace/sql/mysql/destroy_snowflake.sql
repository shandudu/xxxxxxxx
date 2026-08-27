delete from sys_menu where name in ('MesTraceView', 'MesTraceRuleConfig', 'MesTraceLotConfig', 'MesTraceSerialGenerate', 'MesTraceRelationConfig', 'MesTraceQuery');
delete from sys_menu where name = 'MesTrace';
drop table if exists mes_trace_operation_log;
drop table if exists mes_trace_code_sequence;
drop table if exists mes_trace_relation;
drop table if exists mes_material_serial;
drop table if exists mes_material_lot;
drop table if exists mes_material_trace_rule;
drop table if exists mes_trace_code_rule;
