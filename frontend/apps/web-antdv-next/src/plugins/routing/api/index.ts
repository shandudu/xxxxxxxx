import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const operationUrl = '/api/v1/mes/operation';
const workCenterUrl = '/api/v1/mes/work-center';
const routingUrl = '/api/v1/mes/routing';
const materialUrl = '/api/v1/mes/material';

export type OperationStatus = 'ACTIVE' | 'DISABLED';
export type OperationType = 'ASSEMBLY' | 'INSPECTION' | 'OTHER' | 'PACKAGING' | 'PROCESS' | 'TRANSFER';
export type RoutingStatus = 'ACTIVE' | 'DRAFT' | 'INACTIVE';
export type RoutingType = 'REWORK' | 'STANDARD' | 'TRIAL';
export type RunTimeUnit = 'HOUR_PER_BASE_QTY' | 'MIN_PER_BASE_QTY' | 'SEC_PER_BASE_QTY';
export type WorkCenterStatus = 'ACTIVE' | 'DISABLED';
export type WorkCenterType = 'CELL' | 'INSPECTION' | 'MACHINE_GROUP' | 'MANUAL' | 'OTHER' | 'PACKAGING' | 'PRODUCTION_LINE';

export interface PageResult<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export interface MaterialSummary {
  id: number;
  code: string;
  name: string;
  specification?: string;
  unit: string;
}

export interface ProductOption extends MaterialSummary {}

export interface OperationSummary {
  id: number;
  code: string;
  name: string;
  status: OperationStatus;
  operation_type: OperationType;
}

export interface WorkCenterSummary {
  id: number;
  code: string;
  name: string;
  status: WorkCenterStatus;
  production_enabled: boolean;
}

export interface OperationItem {
  id: number;
  operation_code: string;
  operation_name: string;
  operation_short_name?: string;
  operation_type: OperationType;
  description?: string;
  status: OperationStatus;
  production_enabled: boolean;
  quality_enabled: boolean;
  trace_enabled: boolean;
  remark?: string;
  sort_no: number;
  created_time?: string;
  updated_time?: string;
}

export interface OperationOption extends OperationSummary {
  operation_short_name?: string;
  quality_enabled: boolean;
  trace_enabled: boolean;
}

export interface WorkCenterItem {
  id: number;
  work_center_code: string;
  work_center_name: string;
  work_center_type: WorkCenterType;
  factory_code?: string;
  workshop_code?: string;
  location_description?: string;
  status: WorkCenterStatus;
  production_enabled: boolean;
  scheduling_enabled: boolean;
  capacity_value?: number;
  capacity_unit?: string;
  parallel_capacity: number;
  remark?: string;
  sort_no: number;
  created_time?: string;
  updated_time?: string;
}

export interface WorkCenterOption extends WorkCenterSummary {
  work_center_type: WorkCenterType;
  factory_code?: string;
  workshop_code?: string;
}

export interface RoutingOperationItem {
  id: number;
  routing_id: number;
  sequence_no: number;
  operation_id: number;
  work_center_id?: number;
  operation_name_override?: string;
  operation_name_snapshot?: string;
  operation_display_name: string;
  setup_time_min: number;
  run_time_value: number;
  run_time_unit: RunTimeUnit;
  queue_time_min: number;
  move_time_min: number;
  standard_yield_rate: number;
  reporting_required: boolean;
  quality_required: boolean;
  trace_required: boolean;
  remark?: string;
  sort_no: number;
  operation: OperationSummary;
  work_center?: WorkCenterSummary;
}

export interface RoutingItem {
  id: number;
  routing_code: string;
  routing_name: string;
  product_material_id: number;
  routing_version: string;
  routing_type: RoutingType;
  base_quantity: number;
  status: RoutingStatus;
  effective_from?: string;
  effective_to?: string;
  is_default: boolean;
  description?: string;
  remark?: string;
  product: MaterialSummary;
  operation_count: number;
  created_time?: string;
  updated_time?: string;
  operations?: RoutingOperationItem[];
}

export interface RoutingOption {
  id: number;
  code: string;
  name: string;
  version: string;
  routing_type: RoutingType;
  is_default: boolean;
}

export interface RoutingValidationResult {
  valid: boolean;
  errors: { code: string; message: string }[];
  warnings: { code: string; message: string }[];
}

export interface RoutingTimeCalculation {
  routing_id: number;
  production_quantity: number;
  base_quantity: number;
  total_time_min: number;
  items: Array<{
    routing_operation_id: number;
    sequence_no: number;
    operation_name: string;
    setup_time_min: number;
    run_time_min: number;
    queue_time_min: number;
    move_time_min: number;
    total_time_min: number;
  }>;
}

export function getOperationsApi(params?: Recordable<any>) {
  return requestClient.get<PageResult<OperationItem>>(operationUrl, { params });
}
export function getOperationApi(id: number) { return requestClient.get<OperationItem>(`${operationUrl}/${id}`); }
export function createOperationApi(data: Recordable<any>) { return requestClient.post<OperationItem>(operationUrl, data); }
export function updateOperationApi(id: number, data: Recordable<any>) { return requestClient.put<OperationItem>(`${operationUrl}/${id}`, data); }
export function updateOperationStatusApi(id: number, status: OperationStatus) { return requestClient.put<OperationItem>(`${operationUrl}/${id}/status`, { status }); }
export function getOperationOptionsApi(params?: Recordable<any>) { return requestClient.get<OperationOption[]>(`${operationUrl}/options`, { params }); }

export function getWorkCentersApi(params?: Recordable<any>) { return requestClient.get<PageResult<WorkCenterItem>>(workCenterUrl, { params }); }
export function getWorkCenterApi(id: number) { return requestClient.get<WorkCenterItem>(`${workCenterUrl}/${id}`); }
export function createWorkCenterApi(data: Recordable<any>) { return requestClient.post<WorkCenterItem>(workCenterUrl, data); }
export function updateWorkCenterApi(id: number, data: Recordable<any>) { return requestClient.put<WorkCenterItem>(`${workCenterUrl}/${id}`, data); }
export function updateWorkCenterStatusApi(id: number, status: WorkCenterStatus) { return requestClient.put<WorkCenterItem>(`${workCenterUrl}/${id}/status`, { status }); }
export function getWorkCenterOptionsApi(params?: Recordable<any>) { return requestClient.get<WorkCenterOption[]>(`${workCenterUrl}/options`, { params }); }

export function getRoutingsApi(params?: Recordable<any>) { return requestClient.get<PageResult<RoutingItem>>(routingUrl, { params }); }
export function getProductOptionsApi(keyword?: string) { return requestClient.get<ProductOption[]>(`${materialUrl}/options`, { params: { keyword, producible: true } }); }
export function getRoutingApi(id: number) { return requestClient.get<RoutingItem>(`${routingUrl}/${id}`); }
export function createRoutingApi(data: Recordable<any>) { return requestClient.post<RoutingItem>(routingUrl, data); }
export function updateRoutingApi(id: number, data: Recordable<any>) { return requestClient.put<RoutingItem>(`${routingUrl}/${id}`, data); }
export function copyRoutingApi(id: number, data: Recordable<any>) { return requestClient.post<RoutingItem>(`${routingUrl}/${id}/copy`, data); }
export function validateRoutingApi(id: number) { return requestClient.post<RoutingValidationResult>(`${routingUrl}/${id}/validate`); }
export function activateRoutingApi(id: number, setAsDefault = false) { return requestClient.post<RoutingItem>(`${routingUrl}/${id}/activate`, { set_as_default: setAsDefault }); }
export function deactivateRoutingApi(id: number) { return requestClient.post<RoutingItem>(`${routingUrl}/${id}/deactivate`); }
export function setDefaultRoutingApi(id: number) { return requestClient.put<RoutingItem>(`${routingUrl}/${id}/default`); }
export function calculateRoutingTimeApi(id: number, productionQuantity: number) { return requestClient.post<RoutingTimeCalculation>(`${routingUrl}/${id}/calculate-time`, { production_quantity: productionQuantity }); }
export function createRoutingOperationApi(routingId: number, data: Recordable<any>) { return requestClient.post<RoutingOperationItem>(`${routingUrl}/${routingId}/operations`, data); }
export function updateRoutingOperationApi(routingId: number, id: number, data: Recordable<any>) { return requestClient.put<RoutingOperationItem>(`${routingUrl}/${routingId}/operations/${id}`, data); }
export function deleteRoutingOperationApi(routingId: number, id: number) { return requestClient.delete(`${routingUrl}/${routingId}/operations/${id}`); }
export function reorderRoutingOperationsApi(routingId: number, items: { routing_operation_id: number; sequence_no: number }[]) { return requestClient.put<RoutingOperationItem[]>(`${routingUrl}/${routingId}/operations/reorder`, { items }); }
