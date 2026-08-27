import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/maintenance';

export type MaintenancePlanType = 'INSPECTION' | 'PREVENTIVE';
export type CycleUnit = 'DAY' | 'MONTH' | 'WEEK';
export type PlanStatus = 'ACTIVE' | 'DISABLED';
export type TaskStatus = 'CANCELLED' | 'COMPLETED' | 'IN_PROGRESS' | 'PENDING';
export type TaskResult = 'FAIL' | 'NA' | 'PASS';
export type FaultLevel = 'CRITICAL' | 'MAJOR' | 'MINOR';
export type RepairStatus = 'ASSIGNED' | 'CANCELLED' | 'COMPLETED' | 'IN_REPAIR' | 'REPORTED';
export type DowntimeCategory = 'PLANNED' | 'UNPLANNED';
export type DowntimeSourceType = 'INSPECTION' | 'MAINTENANCE' | 'MANUAL' | 'REPAIR';
export type DowntimeStatus = 'CANCELLED' | 'CLOSED' | 'OPEN';

export interface MaintenanceDashboard {
  active_plans: number;
  pending_tasks: number;
  overdue_tasks: number;
  in_progress_tasks: number;
  open_repairs: number;
  critical_repairs: number;
  open_downtimes: number;
  downtime_minutes_30d: number;
  completion_rate_30d: number;
}

export interface MaintenancePlan {
  id: number;
  plan_no: string;
  plan_name: string;
  equipment_id: number;
  equipment_code: string;
  equipment_name: string;
  work_center_id?: number;
  work_center_name?: string;
  plan_type: MaintenancePlanType;
  cycle_unit: CycleUnit;
  cycle_value: number;
  next_due_date: string;
  lead_days: number;
  estimated_minutes: number;
  requires_shutdown: boolean;
  assigned_user_id?: number;
  assigned_username?: string;
  checklist_items: string[];
  status: PlanStatus;
  last_generated_date?: string;
  remark?: string;
  created_time: string;
  updated_time?: string;
}

export interface MaintenanceTask {
  id: number;
  task_no: string;
  plan_id: number;
  plan_name: string;
  equipment_id: number;
  equipment_code: string;
  equipment_name: string;
  work_center_id?: number;
  work_center_name?: string;
  task_type: MaintenancePlanType;
  due_date: string;
  assigned_user_id?: number;
  assigned_username?: string;
  estimated_minutes: number;
  requires_shutdown: boolean;
  checklist_items: string[];
  checklist_results: Array<Record<string, any>>;
  status: TaskStatus;
  result?: TaskResult;
  overdue: boolean;
  started_at?: string;
  completed_at?: string;
  downtime_id?: number;
  findings?: string;
  action_taken?: string;
  remark?: string;
  created_time: string;
}

export interface RepairOrder {
  id: number;
  repair_no: string;
  equipment_id: number;
  equipment_code: string;
  equipment_name: string;
  work_center_id?: number;
  work_center_name?: string;
  fault_level: FaultLevel;
  fault_description: string;
  reported_at: string;
  assigned_user_id?: number;
  assigned_username?: string;
  status: RepairStatus;
  affects_capacity: boolean;
  downtime_id?: number;
  reported_by?: number;
  started_at?: string;
  completed_at?: string;
  root_cause?: string;
  repair_action?: string;
  spare_parts_used?: string;
  repair_cost: number;
  remark?: string;
  created_time: string;
}

export interface EquipmentDowntime {
  id: number;
  downtime_no: string;
  equipment_id: number;
  equipment_code: string;
  equipment_name: string;
  work_center_id?: number;
  work_center_name?: string;
  category: DowntimeCategory;
  source_type: DowntimeSourceType;
  source_id?: number;
  start_at: string;
  end_at?: string;
  status: DowntimeStatus;
  affects_capacity: boolean;
  reason?: string;
  duration_minutes?: number;
  remark?: string;
  created_time: string;
}

export interface EquipmentOption {
  id: number;
  code: string;
  name: string;
  status: string;
  type: string;
}

export interface WorkCenterOption {
  id: number;
  code: string;
  name: string;
  status: string;
  production_enabled: boolean;
}

export interface UserOption {
  id: number;
  username: string;
  nickname: string;
  status: number;
}

export interface PageResult<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export const getMaintenanceDashboardApi = () =>
  requestClient.get<MaintenanceDashboard>(`${baseUrl}/dashboard`);

export const getMaintenancePlansApi = () =>
  requestClient.get<MaintenancePlan[]>(`${baseUrl}/plans`);
export const createMaintenancePlanApi = (data: Recordable<any>) =>
  requestClient.post<MaintenancePlan>(`${baseUrl}/plans`, data);
export const updateMaintenancePlanApi = (id: number, data: Recordable<any>) =>
  requestClient.put<MaintenancePlan>(`${baseUrl}/plans/${id}`, data);
export const generateDueTasksApi = (data: Recordable<any>) =>
  requestClient.post<MaintenanceTask[]>(`${baseUrl}/plans/generate-due`, data);

export const getMaintenanceTasksApi = () =>
  requestClient.get<MaintenanceTask[]>(`${baseUrl}/tasks`);
export const startMaintenanceTaskApi = (id: number, data: Recordable<any> = {}) =>
  requestClient.post<MaintenanceTask>(`${baseUrl}/tasks/${id}/start`, data);
export const completeMaintenanceTaskApi = (id: number, data: Recordable<any>) =>
  requestClient.post<MaintenanceTask>(`${baseUrl}/tasks/${id}/complete`, data);

export const getRepairOrdersApi = () =>
  requestClient.get<RepairOrder[]>(`${baseUrl}/repairs`);
export const createRepairOrderApi = (data: Recordable<any>) =>
  requestClient.post<RepairOrder>(`${baseUrl}/repairs`, data);
export const assignRepairOrderApi = (id: number, data: Recordable<any>) =>
  requestClient.post<RepairOrder>(`${baseUrl}/repairs/${id}/assign`, data);
export const startRepairOrderApi = (id: number, data: Recordable<any> = {}) =>
  requestClient.post<RepairOrder>(`${baseUrl}/repairs/${id}/start`, data);
export const completeRepairOrderApi = (id: number, data: Recordable<any>) =>
  requestClient.post<RepairOrder>(`${baseUrl}/repairs/${id}/complete`, data);
export const cancelRepairOrderApi = (id: number) =>
  requestClient.post<RepairOrder>(`${baseUrl}/repairs/${id}/cancel`);

export const getEquipmentDowntimesApi = () =>
  requestClient.get<EquipmentDowntime[]>(`${baseUrl}/downtimes`);
export const createEquipmentDowntimeApi = (data: Recordable<any>) =>
  requestClient.post<EquipmentDowntime>(`${baseUrl}/downtimes`, data);
export const closeEquipmentDowntimeApi = (id: number, data: Recordable<any>) =>
  requestClient.post<EquipmentDowntime>(`${baseUrl}/downtimes/${id}/close`, data);

export const getMaintenanceEquipmentOptionsApi = () =>
  requestClient.get<EquipmentOption[]>('/api/v1/mes/equipment/options', {
    params: { maintenance_enabled: true },
  });
export const getMaintenanceWorkCenterOptionsApi = () =>
  requestClient.get<WorkCenterOption[]>('/api/v1/mes/work-center/options');
export const getMaintenanceUserOptionsApi = () =>
  requestClient.get<PageResult<UserOption>>('/api/v1/sys/users', {
    params: { page: 1, size: 200, status: 1 },
  });
