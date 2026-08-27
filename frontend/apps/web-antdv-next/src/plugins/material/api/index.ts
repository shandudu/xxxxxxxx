import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/material';

export type MaterialType =
  | 'AUXILIARY'
  | 'CONSUMABLE'
  | 'FINISHED_PRODUCT'
  | 'PACKAGING'
  | 'RAW_MATERIAL'
  | 'SEMI_FINISHED'
  | 'SPARE_PART';
export type MaterialStatus = 'ACTIVE' | 'DISABLED';

export interface CategoryTreeNode {
  id: number;
  code: string;
  name: string;
  parent_id?: number;
  status: MaterialStatus;
  sort_no: number;
  remark?: string;
  children: CategoryTreeNode[];
}

export interface UnitItem {
  id: number;
  unit_code: string;
  unit_name: string;
  symbol?: string;
  status: MaterialStatus;
  decimal_places: number;
}

export interface WarehouseOption {
  id: number;
  code: string;
  name: string;
  status: string;
}

export interface MaterialItem {
  id: number;
  material_code: string;
  material_name: string;
  material_short_name?: string;
  material_type: MaterialType;
  category_id: number;
  category_name?: string;
  base_unit_id: number;
  unit_code?: string;
  specification?: string;
  model?: string;
  status: MaterialStatus;
  batch_control: boolean;
  serial_control: boolean;
  purchasable: boolean;
  producible: boolean;
  sellable: boolean;
  quality_inspection_required: boolean;
  default_warehouse_id?: number;
  warehouse_name?: string;
  shelf_life_days?: number;
  remark?: string;
  created_time: string;
  updated_time?: string;
}

export interface MaterialOption {
  id: number;
  code: string;
  name: string;
  specification?: string;
  unit: string;
}

export type MaterialForm = Omit<
  MaterialItem,
  | 'category_name'
  | 'created_time'
  | 'id'
  | 'unit_code'
  | 'updated_time'
  | 'warehouse_name'
> & { id?: number };

export function getMaterialCategoryTreeApi() {
  return requestClient.get<CategoryTreeNode[]>(`${baseUrl}/category/tree`);
}

export function getMaterialUnitListApi() {
  return requestClient.get<UnitItem[]>(`${baseUrl}/unit`);
}

export function getMaterialWarehouseOptionsApi() {
  return requestClient.get<WarehouseOption[]>(`${baseUrl}/warehouse`);
}

export function getMaterialListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<MaterialItem>>(baseUrl, { params });
}

export function getMaterialApi(id: number) {
  return requestClient.get<MaterialItem>(`${baseUrl}/${id}`);
}

export function createMaterialApi(data: MaterialForm) {
  return requestClient.post<MaterialItem>(baseUrl, data);
}

export function updateMaterialApi(id: number, data: MaterialForm) {
  return requestClient.put<MaterialItem>(`${baseUrl}/${id}`, data);
}

export function updateMaterialStatusApi(id: number, status: MaterialStatus) {
  return requestClient.put<MaterialItem>(`${baseUrl}/${id}/status`, { status });
}

export function getMaterialOptionsApi(params?: Recordable<any>) {
  return requestClient.get<MaterialOption[]>(`${baseUrl}/options`, { params });
}
