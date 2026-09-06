import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/packaging';

export interface PackagingSpecification {
  allow_mixed_lot: boolean;
  allow_partial_carton: boolean;
  cartons_per_pallet?: number;
  id: number;
  label_template_code?: string;
  material_id: number;
  require_quality_release: boolean;
  require_weight_check: boolean;
  spec_code: string;
  spec_name: string;
  status: string;
  target_gross_weight?: number | string;
  units_per_carton: number | string;
  version: string;
  weight_tolerance?: number | string;
}

export interface PackagingContent {
  id: number;
  lot_id?: number;
  quantity: number | string;
  scan_type: string;
  scanned_code: string;
  serial_id?: number;
}

export interface HandlingUnit {
  capacity: number | string;
  contents: PackagingContent[];
  gross_weight?: number | string;
  hu_code: string;
  hu_type: string;
  id: number;
  quantity: number | string;
  status: string;
  weight_result?: string;
}

export interface PackagingTask {
  handling_units: HandlingUnit[];
  id: number;
  lot_id?: number;
  material_id: number;
  packed_quantity: number | string;
  planned_quantity: number | string;
  production_report_id: number;
  specification_id: number;
  status: string;
  task_no: string;
  work_order_id: number;
}

export interface PackagingDashboard {
  active_tasks: number;
  draft_tasks: number;
  held_handling_units: number;
  open_handling_units: number;
  packed_quantity: number | string;
  packed_tasks: number;
  planned_quantity: number | string;
  released_tasks: number;
}

export const getPackagingDashboardApi = () => requestClient.get<PackagingDashboard>(`${baseUrl}/dashboard`);
export const getPackagingSpecificationsApi = () => requestClient.get<PackagingSpecification[]>(`${baseUrl}/specifications`);
export const createPackagingSpecificationApi = (data: Recordable<any>) => requestClient.post<PackagingSpecification>(`${baseUrl}/specifications`, data);
export const getPackagingTasksApi = () => requestClient.get<PackagingTask[]>(`${baseUrl}/tasks`);
export const createPackagingTaskApi = (data: Recordable<any>) => requestClient.post<PackagingTask>(`${baseUrl}/tasks`, data);
export const releasePackagingTaskApi = (id: number) => requestClient.post<PackagingTask>(`${baseUrl}/tasks/${id}/release`);
export const startPackagingTaskApi = (id: number) => requestClient.post<PackagingTask>(`${baseUrl}/tasks/${id}/start`);
export const createHandlingUnitApi = (id: number, data: Recordable<any>) => requestClient.post<HandlingUnit>(`${baseUrl}/tasks/${id}/handling-units`, data);
export const scanPackagingItemApi = (id: number, data: Recordable<any>) => requestClient.post<HandlingUnit>(`${baseUrl}/handling-units/${id}/scan`, data);
export const recordPackagingWeightApi = (id: number, data: Recordable<any>) => requestClient.post(`${baseUrl}/handling-units/${id}/weight`, data);
export const sealHandlingUnitApi = (id: number, data: Recordable<any>) => requestClient.post<HandlingUnit>(`${baseUrl}/handling-units/${id}/seal`, data);
export const inspectHandlingUnitApi = (id: number, data: Recordable<any>) => requestClient.post(`${baseUrl}/handling-units/${id}/inspection`, data);
export const printPackagingLabelApi = (id: number, data: Recordable<any>) => requestClient.post(`${baseUrl}/handling-units/${id}/labels`, data);
export const releasePackagingToStockApi = (id: number) => requestClient.post<PackagingTask>(`${baseUrl}/tasks/${id}/release-to-stock`);
