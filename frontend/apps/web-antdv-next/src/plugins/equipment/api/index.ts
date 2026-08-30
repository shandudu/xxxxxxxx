import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/equipment';

export type EquipmentType =
  | 'INSPECTION'
  | 'LOGISTICS'
  | 'OTHER'
  | 'PRODUCTION'
  | 'TOOL'
  | 'UTILITY';
export type EquipmentStatus = 'DISABLED' | 'DOWN' | 'IDLE' | 'MAINTENANCE' | 'OFFLINE' | 'RUNNING';
export type EquipmentCategoryStatus = 'ACTIVE' | 'DISABLED';

export interface EquipmentCategory {
  id: number;
  category_code: string;
  category_name: string;
  parent_id?: number;
  status: EquipmentCategoryStatus;
  sort_no: number;
  remark?: string;
}

export interface EquipmentCategoryTreeNode {
  id: number;
  code: string;
  name: string;
  parent_id?: number;
  status: EquipmentCategoryStatus;
  sort_no: number;
  remark?: string;
  children: EquipmentCategoryTreeNode[];
}

export interface EquipmentItem {
  id: number;
  equipment_code: string;
  equipment_name: string;
  category_id: number;
  category_name?: string;
  equipment_type: EquipmentType;
  model?: string;
  manufacturer?: string;
  serial_number?: string;
  factory_code?: string;
  area_code?: string;
  installation_location?: string;
  status: EquipmentStatus;
  enabled: boolean;
  production_enabled: boolean;
  data_collection_enabled: boolean;
  maintenance_enabled: boolean;
  commission_date?: string;
  service_date?: string;
  rated_capacity?: number | string;
  capacity_unit?: string;
  remark?: string;
  created_time: string;
  updated_time?: string;
  created_by?: number;
  updated_by?: number;
}

export interface EquipmentOption {
  id: number;
  code: string;
  name: string;
  type: EquipmentType;
  status: EquipmentStatus;
}

export type EquipmentForm = Omit<
  EquipmentItem,
  | 'category_name'
  | 'created_by'
  | 'created_time'
  | 'id'
  | 'status'
  | 'updated_by'
  | 'updated_time'
> & { id?: number };

export type EquipmentCategoryForm = Omit<EquipmentCategory, 'id'> & { id?: number };

export function getEquipmentCategoryTreeApi() {
  return requestClient.get<EquipmentCategoryTreeNode[]>(`${baseUrl}/category/tree`);
}

export function createEquipmentCategoryApi(data: EquipmentCategoryForm) {
  return requestClient.post<EquipmentCategory>(`${baseUrl}/category`, data);
}

export function updateEquipmentCategoryApi(id: number, data: EquipmentCategoryForm) {
  return requestClient.put<EquipmentCategory>(`${baseUrl}/category/${id}`, data);
}

export function getEquipmentListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<EquipmentItem>>(baseUrl, { params });
}

export function getEquipmentApi(id: number) {
  return requestClient.get<EquipmentItem>(`${baseUrl}/${id}`);
}

export function createEquipmentApi(data: EquipmentForm) {
  return requestClient.post<EquipmentItem>(baseUrl, data);
}

export function updateEquipmentApi(id: number, data: EquipmentForm) {
  return requestClient.put<EquipmentItem>(`${baseUrl}/${id}`, data);
}

export function updateEquipmentEnabledApi(id: number, enabled: boolean) {
  return requestClient.put<EquipmentItem>(`${baseUrl}/${id}/enabled`, { enabled });
}

export function updateEquipmentStatusApi(id: number, status: EquipmentStatus) {
  return requestClient.put<EquipmentItem>(`${baseUrl}/${id}/status`, { status });
}

export function getEquipmentOptionsApi(params?: Recordable<any>) {
  return requestClient.get<EquipmentOption[]>(`${baseUrl}/options`, { params });
}

export interface MoldDashboard { total_molds: number; mounted_molds: number; maintenance_due: number; life_warning: number; life_exceeded: number; blocked_cavities: number; open_maintenance_orders: number; total_lifecycle_cost: number; }
export interface MoldItem { id: number; mold_code: string; mold_name: string; tool_equipment_id: number; product_material_id: number; mold_type: string; cavity_count: number; designed_life_shots: number; maintenance_interval_shots: number; status: string; warning_percent: number; current_shots: number; shots_since_maintenance: number; mounted_equipment_id?: number; acquisition_cost: number; residual_value: number; next_maintenance_shots?: number; location?: string; manufacturer?: string; }
export interface MoldCavity { id: number; mold_id: number; cavity_no: string; status: string; current_shots: number; inspected_quantity: number; defect_quantity: number; last_defect_code?: string; }
export interface MoldMount { id: number; mount_no: string; mold_id: number; equipment_id: number; work_order_id?: number; mounted_at: string; status: string; opening_shots: number; closing_shots?: number; produced_quantity: number; good_quantity: number; scrap_quantity: number; }
export interface MoldMaintenance { id: number; order_no: string; mold_id: number; maintenance_type: string; trigger_type: string; description: string; status: string; due_shots?: number; findings?: string; action_taken?: string; total_cost: number; }
export interface MoldCostAnalysis { mold_id: number; acquisition_cost: number; maintenance_cost: number; repair_cost: number; modification_cost: number; total_lifecycle_cost: number; current_shots: number; cost_per_shot: number; }

const moldsUrl = `${baseUrl}/molds`;
export const getMoldDashboardApi = () => requestClient.get<MoldDashboard>(`${moldsUrl}/dashboard`);
export const getMoldsApi = (params?: Recordable<any>) => requestClient.get<MoldItem[]>(moldsUrl, { params });
export const createMoldApi = (data: Recordable<any>) => requestClient.post<MoldItem>(moldsUrl, data);
export const updateMoldStatusApi = (id: number, data: Recordable<any>) => requestClient.put<MoldItem>(`${moldsUrl}/${id}/status`, data);
export const getMoldCavitiesApi = (id: number) => requestClient.get<MoldCavity[]>(`${moldsUrl}/${id}/cavities`);
export const updateMoldCavityApi = (id: number, data: Recordable<any>) => requestClient.put<MoldCavity>(`${moldsUrl}/cavities/${id}`, data);
export const mountMoldApi = (id: number, data: Recordable<any>) => requestClient.post<MoldMount>(`${moldsUrl}/${id}/mount`, data);
export const unmountMoldApi = (id: number, data: Recordable<any> = {}) => requestClient.post<MoldMount>(`${moldsUrl}/${id}/unmount`, data);
export const getMoldMountsApi = (params?: Recordable<any>) => requestClient.get<MoldMount[]>(`${moldsUrl}/mounts/history`, { params });
export const getMoldMaintenanceApi = (params?: Recordable<any>) => requestClient.get<MoldMaintenance[]>(`${moldsUrl}/maintenance/orders`, { params });
export const createMoldMaintenanceApi = (id: number, data: Recordable<any>) => requestClient.post<MoldMaintenance>(`${moldsUrl}/${id}/maintenance`, data);
export const startMoldMaintenanceApi = (id: number) => requestClient.post<MoldMaintenance>(`${moldsUrl}/maintenance/${id}/start`);
export const completeMoldMaintenanceApi = (id: number, data: Recordable<any>) => requestClient.post<MoldMaintenance>(`${moldsUrl}/maintenance/${id}/complete`, data);
export const recordMoldQualityApi = (id: number, data: Recordable<any>) => requestClient.post(`${moldsUrl}/${id}/quality`, data);
export const getMoldCostAnalysisApi = (id: number) => requestClient.get<MoldCostAnalysis>(`${moldsUrl}/${id}/cost-analysis`);
