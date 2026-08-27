import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/planning';

export type MpsPlanStatus = 'CLOSED' | 'CONFIRMED' | 'DRAFT';
export type MpsDemandType = 'FORECAST' | 'MANUAL' | 'SALES_ORDER';
export type MrpRunStatus = 'COMPLETED' | 'FAILED' | 'RUNNING';
export type PlannedOrderType = 'PRODUCTION' | 'PURCHASE';
export type PlannedOrderStatus = 'CANCELLED' | 'FIRM' | 'PLANNED' | 'RELEASED';

export interface MpsDemand {
  id: number;
  mps_plan_id: number;
  line_no: number;
  material_id: number;
  unit_id: number;
  demand_type: MpsDemandType;
  demand_date: string;
  quantity: number;
  material_code_snapshot: string;
  material_name_snapshot: string;
  unit_code_snapshot: string;
  source_id?: number;
  source_no?: string;
  remark?: string;
  created_time: string;
}

export interface MpsPlan {
  id: number;
  plan_no: string;
  plan_name: string;
  horizon_start: string;
  horizon_end: string;
  status: MpsPlanStatus;
  remark?: string;
  created_time: string;
  updated_time?: string;
  demands: MpsDemand[];
}

export interface MrpRequirement {
  id: number;
  mrp_run_id: number;
  sequence_no: number;
  mps_demand_id: number;
  level_no: number;
  material_id: number;
  parent_material_id?: number;
  bom_id?: number;
  bom_item_id?: number;
  requirement_date: string;
  gross_requirement: number;
  on_hand_allocated: number;
  purchase_supply_allocated: number;
  production_supply_allocated: number;
  net_requirement: number;
  planned_order_quantity: number;
  uncovered_quantity: number;
  material_code_snapshot: string;
  material_name_snapshot: string;
  unit_code_snapshot: string;
  source_path: string;
}

export interface PlannedOrder {
  id: number;
  planned_order_no: string;
  mrp_run_id: number;
  mrp_requirement_id: number;
  sequence_no: number;
  material_id: number;
  order_type: PlannedOrderType;
  status: PlannedOrderStatus;
  quantity: number;
  release_date: string;
  due_date: string;
  material_code_snapshot: string;
  material_name_snapshot: string;
  unit_code_snapshot: string;
  bom_id?: number;
  source_document_type?: string;
  source_document_id?: number;
  source_document_no?: string;
  firmed_at?: string;
  released_at?: string;
  remark?: string;
}

export interface MrpRun {
  id: number;
  run_no: string;
  mps_plan_id: number;
  status: MrpRunStatus;
  include_inventory: boolean;
  include_open_purchase: boolean;
  include_open_production: boolean;
  default_purchase_lead_days: number;
  default_production_lead_days: number;
  max_level: number;
  requirement_count: number;
  planned_order_count: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  promise_refresh_at?: string;
  promise_assessment_count: number;
  created_time: string;
  requirements: MrpRequirement[];
  planned_orders: PlannedOrder[];
}

export const getMpsPlansApi = (params?: Recordable<any>) =>
  requestClient.get<MpsPlan[]>(`${baseUrl}/mps-plans`, { params });
export const getMpsPlanApi = (id: number) =>
  requestClient.get<MpsPlan>(`${baseUrl}/mps-plans/${id}`);
export const createMpsPlanApi = (data: Recordable<any>) =>
  requestClient.post<MpsPlan>(`${baseUrl}/mps-plans`, data);
export const addMpsDemandApi = (id: number, data: Recordable<any>) =>
  requestClient.post<MpsDemand>(`${baseUrl}/mps-plans/${id}/demands`, data);
export const importSalesOrdersApi = (id: number, data: Recordable<any>) =>
  requestClient.post<MpsDemand[]>(`${baseUrl}/mps-plans/${id}/import-sales-orders`, data);
export const deleteMpsDemandApi = (planId: number, demandId: number) =>
  requestClient.delete(`${baseUrl}/mps-plans/${planId}/demands/${demandId}`);
export const confirmMpsPlanApi = (id: number) =>
  requestClient.post<MpsPlan>(`${baseUrl}/mps-plans/${id}/confirm`);

export const getMrpRunsApi = (params?: Recordable<any>) =>
  requestClient.get<MrpRun[]>(`${baseUrl}/mrp-runs`, { params });
export const getMrpRunApi = (id: number) =>
  requestClient.get<MrpRun>(`${baseUrl}/mrp-runs/${id}`);
export const runMrpApi = (data: Recordable<any>) =>
  requestClient.post<MrpRun>(`${baseUrl}/mrp-runs`, data);
export const firmPlannedOrderApi = (id: number) =>
  requestClient.post<PlannedOrder>(`${baseUrl}/planned-orders/${id}/firm`);
export const releasePlannedOrderApi = (id: number, data: Recordable<any>) =>
  requestClient.post<PlannedOrder>(`${baseUrl}/planned-orders/${id}/release`, data);
export const recalculateOpenOrderPromisesApi = () =>
  requestClient.post<{ assessed_order_count: number; assessed_line_count: number; assessed_at: string }>(
    '/api/v1/erp/sales/promise/recalculate',
  );
