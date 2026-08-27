import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/trace';

export type TraceRuleType = 'LOT' | 'SERIAL';
export type RuleStatus = 'ACTIVE' | 'DISABLED';
export type LotStatus = 'ACTIVE' | 'HOLD' | 'CONSUMED' | 'CLOSED' | 'DISABLED';
export type SerialStatus = 'ACTIVE' | 'HOLD' | 'SCRAPPED' | 'CONSUMED' | 'SHIPPED' | 'DISABLED';
export type ObjectType = 'LOT' | 'SERIAL';

export interface TraceRule {
  id: number;
  rule_code: string;
  rule_name: string;
  rule_type: TraceRuleType;
  pattern: string;
  sequence_length: number;
  sequence_reset_type: 'NEVER' | 'YEARLY' | 'MONTHLY' | 'DAILY';
  prefix?: string;
  status: RuleStatus;
  example?: string;
  remark?: string;
}

export interface MaterialTraceRule {
  id?: number;
  material_id: number;
  lot_rule_id?: number;
  serial_rule_id?: number;
}

export interface LotItem {
  id: number;
  lot_no: string;
  material_id: number;
  material_code?: string;
  material_name?: string;
  lot_type: string;
  quantity?: number;
  unit_id?: number;
  unit_code?: string;
  status: LotStatus;
  quality_status: string;
  production_date?: string;
  expiry_date?: string;
  source_type?: string;
  source_ref_no?: string;
  supplier_lot_no?: string;
  remark?: string;
}

export interface SerialItem {
  id: number;
  serial_no: string;
  material_id: number;
  material_code?: string;
  material_name?: string;
  lot_id?: number;
  lot_no?: string;
  status: SerialStatus;
  quality_status: string;
  production_date?: string;
  remark?: string;
}

export interface TraceNode {
  object_type: ObjectType;
  object_id: number;
  code: string;
  material_id: number;
  material_code?: string;
  material_name?: string;
  relation_type?: string;
  quantity?: number;
  unit_id?: number;
  children: TraceNode[];
}

export function getTraceRulesApi(params?: Recordable<any>) {
  return requestClient.get<TraceRule[]>(`${baseUrl}/code-rule`, { params });
}

export function createTraceRuleApi(data: Recordable<any>) {
  return requestClient.post<TraceRule>(`${baseUrl}/code-rule`, data);
}

export function updateTraceRuleApi(id: number, data: Recordable<any>) {
  return requestClient.put<TraceRule>(`${baseUrl}/code-rule/${id}`, data);
}

export function previewTraceRuleApi(data: Recordable<any>) {
  return requestClient.post<{ example: string }>(`${baseUrl}/code-rule/preview`, data);
}

export function getMaterialTraceRuleApi(materialId: number) {
  return requestClient.get<MaterialTraceRule>(`${baseUrl}/material-rule/${materialId}`);
}

export function updateMaterialTraceRuleApi(materialId: number, data: Recordable<any>) {
  return requestClient.put<MaterialTraceRule>(`${baseUrl}/material-rule/${materialId}`, data);
}

export function getLotListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<LotItem>>(`${baseUrl}/lot`, { params });
}

export function getLotApi(id: number) {
  return requestClient.get<LotItem>(`${baseUrl}/lot/${id}`);
}

export function createLotApi(data: Recordable<any>) {
  return requestClient.post<LotItem>(`${baseUrl}/lot`, data);
}

export function updateLotStatusApi(id: number, status: LotStatus) {
  return requestClient.put<LotItem>(`${baseUrl}/lot/${id}/status`, { status });
}

export function splitLotApi(id: number, data: { children: Array<{ lot_no: string; quantity: number }> }) {
  return requestClient.post<LotItem[]>(`${baseUrl}/lot/${id}/split`, data);
}

export function mergeLotsApi(data: Recordable<any>) {
  return requestClient.post<LotItem>(`${baseUrl}/lot/merge`, data);
}

export function getSerialListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<SerialItem>>(`${baseUrl}/serial`, { params });
}

export function generateSerialsApi(data: Recordable<any>) {
  return requestClient.post<{ count: number; serials: string[] }>(`${baseUrl}/serial/generate`, data);
}

export function updateSerialStatusApi(id: number, status: SerialStatus) {
  return requestClient.put<SerialItem>(`${baseUrl}/serial/${id}/status`, { status });
}

export function createTraceRelationApi(data: Recordable<any>) {
  return requestClient.post(`${baseUrl}/relation`, data);
}

export function getForwardTraceApi(type: ObjectType, code: string, maxDepth = 30) {
  return requestClient.get<TraceNode>(`${baseUrl}/forward`, { params: { type, code, max_depth: maxDepth } });
}

export function getBackwardTraceApi(type: ObjectType, code: string, maxDepth = 30) {
  return requestClient.get<TraceNode>(`${baseUrl}/backward`, { params: { type, code, max_depth: maxDepth } });
}

