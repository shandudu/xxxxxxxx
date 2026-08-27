import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/warehouse';

export type WarehouseType =
  | 'FINISHED_PRODUCT'
  | 'LINE_SIDE'
  | 'QUALITY_HOLD'
  | 'RAW_MATERIAL'
  | 'SCRAP'
  | 'VIRTUAL'
  | 'WIP';
export type WarehouseStatus = 'ACTIVE' | 'DISABLED';
export type AreaStatus = 'ACTIVE' | 'DISABLED';
export type LocationStatus = 'AVAILABLE' | 'DISABLED' | 'LOCKED';

export interface WarehouseItem {
  id: number;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type: WarehouseType;
  factory_code?: string;
  status: WarehouseStatus;
  allow_inbound: boolean;
  allow_outbound: boolean;
  remark?: string;
  sort_no: number;
}

export interface AreaItem {
  id: number;
  area_code: string;
  area_name: string;
  warehouse_id: number;
  area_type?: string;
  status: AreaStatus;
  remark?: string;
  sort_no: number;
}

export interface LocationItem {
  id: number;
  warehouse_id: number;
  area_id: number;
  parent_id?: number;
  location_code: string;
  location_name: string;
  location_type: string;
  location_level: number;
  status: LocationStatus;
  storage_enabled: boolean;
  capacity_value?: number;
  capacity_unit?: string;
  mixed_material_allowed: boolean;
  mixed_lot_allowed: boolean;
  remark?: string;
  sort_no: number;
}

export interface WarehouseTreeNode {
  id: number;
  node_type: string;
  code: string;
  name: string;
  status: string;
  storage_enabled?: boolean;
  children?: WarehouseTreeNode[];
}

export interface WarehouseTree {
  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;
  children: WarehouseTreeNode[];
}

export interface LocationSearchResult {
  id: number;
  location_code: string;
  location_name: string;
  path_ids: number[];
  path: string;
}

export interface LocationGenerateParams {
  warehouse_id: number;
  area_id: number;
  parent_id?: number;
  area_prefix: string;
  rack: { start: number; end: number; digits: number };
  level: { start: number; end: number; digits: number };
  bin: { start: number; end: number; digits: number };
  pattern: string;
  location_type: string;
}

export function getWarehouseListApi(params?: Recordable<any>) {
  return requestClient.get<WarehouseItem[]>(baseUrl, { params });
}

export function createWarehouseApi(data: Recordable<any>) {
  return requestClient.post<WarehouseItem>(`${baseUrl}/config`, data);
}

export function updateWarehouseApi(id: number, data: Recordable<any>) {
  return requestClient.put<WarehouseItem>(`${baseUrl}/${id}/config`, data);
}

export function getAreasApi(warehouseId: number) {
  return requestClient.get<AreaItem[]>(`${baseUrl}/${warehouseId}/areas`);
}

export function createAreaApi(data: Recordable<any>) {
  return requestClient.post<AreaItem>(`${baseUrl}/area/config`, data);
}

export function updateAreaApi(id: number, data: Recordable<any>) {
  return requestClient.put<AreaItem>(`${baseUrl}/area/${id}/config`, data);
}

export function getWarehouseTreeApi(warehouseId: number) {
  return requestClient.get<WarehouseTree>(`${baseUrl}/${warehouseId}/tree`);
}

export function searchLocationsApi(warehouseId: number, keyword: string) {
  return requestClient.get<LocationSearchResult[]>(
    `${baseUrl}/${warehouseId}/locations/search`,
    { params: { keyword } },
  );
}

export function createLocationApi(data: Recordable<any>) {
  return requestClient.post<LocationItem>(`${baseUrl}/location/config`, data);
}

export function getLocationApi(id: number) {
  return requestClient.get<LocationItem>(`${baseUrl}/location/${id}`);
}

export function updateLocationApi(id: number, data: Recordable<any>) {
  return requestClient.put<LocationItem>(`${baseUrl}/location/${id}/config`, data);
}

export function updateLocationStatusApi(id: number, status: LocationStatus) {
  return requestClient.put<LocationItem>(`${baseUrl}/location/${id}/status`, { status });
}

export function moveLocationApi(id: number, target_parent_id?: number) {
  return requestClient.put<LocationItem>(`${baseUrl}/location/${id}/move`, {
    target_parent_id,
  });
}

export function previewLocationGenerateApi(data: Recordable<any>) {
  return requestClient.post<{ count: number; examples: string[]; conflicts: string[] }>(
    `${baseUrl}/location/generate-preview`,
    data,
  );
}

export function generateLocationsApi(data: Recordable<any>) {
  return requestClient.post<{ count: number }>(`${baseUrl}/location/generate`, data);
}
