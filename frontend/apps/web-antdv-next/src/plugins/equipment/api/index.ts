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
