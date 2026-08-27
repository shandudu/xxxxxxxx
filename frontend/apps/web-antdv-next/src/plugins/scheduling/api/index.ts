import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/scheduling';

export type ConfigStatus = 'ACTIVE' | 'DISABLED';
export type SchedulingDirection = 'BACKWARD' | 'FORWARD';
export type ScheduleStatus = 'CANCELLED' | 'COMPLETED' | 'FAILED' | 'PUBLISHED' | 'RUNNING';
export type OperationScheduleStatus = 'CANCELLED' | 'COMPLETED' | 'DISPATCHED' | 'IN_PROGRESS' | 'PLANNED' | 'PUBLISHED';
export type DispatchStatus = 'ACCEPTED' | 'CANCELLED' | 'COMPLETED' | 'DISPATCHED' | 'STARTED';

export interface Shift {
  id: number;
  shift_code: string;
  shift_name: string;
  start_time: string;
  end_time: string;
  spans_next_day: boolean;
  break_minutes: number;
  status: ConfigStatus;
  remark?: string;
  created_time: string;
}

export interface CalendarDay {
  id: number;
  calendar_id: number;
  work_date: string;
  is_working_day: boolean;
  shift_id?: number;
  capacity_factor: number;
  remark?: string;
}

export interface WorkCenterCalendar {
  id: number;
  calendar_id: number;
  work_center_id: number;
  work_center_code: string;
  work_center_name: string;
  effective_from: string;
  effective_to?: string;
  capacity_factor: number;
  priority: number;
}

export interface WorkCalendar {
  id: number;
  calendar_code: string;
  calendar_name: string;
  weekday_mask: string;
  timezone_name: string;
  default_shift_id?: number;
  default_shift_name?: string;
  status: ConfigStatus;
  remark?: string;
  days: CalendarDay[];
  assignments: WorkCenterCalendar[];
  created_time: string;
}

export interface WorkOrderCandidate {
  id: number;
  work_order_no: string;
  product_code: string;
  product_name: string;
  planned_quantity: number;
  status: string;
  operation_count: number;
  planned_start_at?: string;
  planned_end_at?: string;
}

export interface OperationSchedule {
  id: number;
  schedule_id: number;
  work_order_id: number;
  work_order_operation_id: number;
  routing_operation_id?: number;
  operation_id: number;
  work_center_id: number;
  sequence_no: number;
  lane_no: number;
  planned_start_at: string;
  planned_end_at: string;
  planned_quantity: number;
  setup_minutes: number;
  run_minutes: number;
  queue_minutes: number;
  move_minutes: number;
  load_minutes: number;
  total_minutes: number;
  work_order_no_snapshot: string;
  product_code_snapshot: string;
  product_name_snapshot: string;
  operation_code_snapshot: string;
  operation_name_snapshot: string;
  work_center_code_snapshot: string;
  work_center_name_snapshot: string;
  status: OperationScheduleStatus;
  is_overdue: boolean;
  dispatch_count: number;
}

export interface ApsSchedule {
  id: number;
  schedule_no: string;
  schedule_name: string;
  direction: SchedulingDirection;
  horizon_start_at: string;
  horizon_end_at: string;
  status: ScheduleStatus;
  include_queue_time: boolean;
  include_move_time: boolean;
  work_order_count: number;
  operation_count: number;
  overdue_operation_count: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  published_at?: string;
  remark?: string;
  created_time: string;
  operations?: OperationSchedule[];
}

export interface WorkCenterLoad {
  work_center_id: number;
  work_center_code: string;
  work_center_name: string;
  parallel_capacity: number;
  available_minutes: number;
  scheduled_load_minutes: number;
  utilization_rate: number;
  overload_minutes: number;
  operation_count: number;
}

export interface Dispatch {
  id: number;
  dispatch_no: string;
  schedule_operation_id: number;
  work_order_id: number;
  work_order_operation_id: number;
  work_center_id: number;
  planned_start_at: string;
  planned_end_at: string;
  dispatch_quantity: number;
  priority: number;
  status: DispatchStatus;
  assigned_user_id?: number;
  assigned_team?: string;
  workstation_code?: string;
  dispatched_at?: string;
  accepted_at?: string;
  remark?: string;
  work_order_no: string;
  operation_name: string;
  work_center_name: string;
  assigned_username?: string;
  created_time: string;
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

export const getShiftsApi = () => requestClient.get<Shift[]>(`${baseUrl}/shifts`);
export const createShiftApi = (data: Recordable<any>) => requestClient.post<Shift>(`${baseUrl}/shifts`, data);
export const updateShiftApi = (id: number, data: Recordable<any>) => requestClient.put<Shift>(`${baseUrl}/shifts/${id}`, data);

export const getCalendarsApi = () => requestClient.get<WorkCalendar[]>(`${baseUrl}/calendars`);
export const getCalendarApi = (id: number) => requestClient.get<WorkCalendar>(`${baseUrl}/calendars/${id}`);
export const createCalendarApi = (data: Recordable<any>) => requestClient.post<WorkCalendar>(`${baseUrl}/calendars`, data);
export const updateCalendarApi = (id: number, data: Recordable<any>) => requestClient.put<WorkCalendar>(`${baseUrl}/calendars/${id}`, data);
export const upsertCalendarDayApi = (id: number, data: Recordable<any>) => requestClient.put<WorkCalendar>(`${baseUrl}/calendars/${id}/days`, data);
export const assignWorkCenterApi = (id: number, data: Recordable<any>) => requestClient.post<WorkCalendar>(`${baseUrl}/calendars/${id}/work-centers`, data);

export const getWorkOrderCandidatesApi = () => requestClient.get<WorkOrderCandidate[]>(`${baseUrl}/work-orders/options`);
export const getSchedulesApi = () => requestClient.get<ApsSchedule[]>(`${baseUrl}/schedules`);
export const getScheduleApi = (id: number) => requestClient.get<ApsSchedule>(`${baseUrl}/schedules/${id}`);
export const runScheduleApi = (data: Recordable<any>) => requestClient.post<ApsSchedule>(`${baseUrl}/schedules`, data);
export const publishScheduleApi = (id: number) => requestClient.post<ApsSchedule>(`${baseUrl}/schedules/${id}/publish`);
export const getScheduleLoadsApi = (id: number) => requestClient.get<WorkCenterLoad[]>(`${baseUrl}/schedules/${id}/loads`);

export const getDispatchesApi = () => requestClient.get<Dispatch[]>(`${baseUrl}/dispatches`);
export const createDispatchApi = (data: Recordable<any>) => requestClient.post<Dispatch>(`${baseUrl}/dispatches`, data);
export const acceptDispatchApi = (id: number) => requestClient.post<Dispatch>(`${baseUrl}/dispatches/${id}/accept`);
export const cancelDispatchApi = (id: number) => requestClient.post<Dispatch>(`${baseUrl}/dispatches/${id}/cancel`);

export const getWorkCenterOptionsApi = () => requestClient.get<WorkCenterOption[]>('/api/v1/mes/work-center/options', { params: { active_only: true } });
export const getUserOptionsApi = () => requestClient.get<PageResult<UserOption>>('/api/v1/sys/users', { params: { page: 1, size: 200, status: 1 } });
