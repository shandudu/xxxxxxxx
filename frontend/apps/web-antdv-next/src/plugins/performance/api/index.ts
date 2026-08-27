import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/performance';

export type MetricGrain = 'DAY' | 'MONTH' | 'WEEK';
export type Numeric = number | string;
export type NullableNumeric = Numeric | null;
export type TargetStatus = 'ACTIVE' | 'DISABLED';

export interface PerformanceQuery extends Recordable<any> {
  end_date?: string;
  start_date?: string;
  work_center_id?: number;
}

export interface MetricValues {
  actual_cycle_seconds?: NullableNumeric;
  actual_run_minutes: Numeric;
  availability_rate: Numeric;
  calendar_minutes: Numeric;
  failure_count: number;
  good_quantity: Numeric;
  ideal_cycle_seconds?: NullableNumeric;
  ideal_run_minutes: Numeric;
  idle_capacity_minutes: Numeric;
  mtbf_minutes?: NullableNumeric;
  mttr_minutes?: NullableNumeric;
  oee_rate: Numeric;
  operating_minutes: Numeric;
  performance_rate: Numeric;
  planned_downtime_minutes: Numeric;
  planned_production_minutes: Numeric;
  quality_rate: Numeric;
  scrap_quantity: Numeric;
  source_execution_count: number;
  throughput_per_hour: Numeric;
  total_quantity: Numeric;
  unplanned_downtime_minutes: Numeric;
  utilization_rate: Numeric;
}

export interface PerformanceDashboard extends MetricValues {
  on_target_center_count: number;
  period_end: string;
  period_start: string;
  target_oee_rate: Numeric;
  work_center_count: number;
}

export interface WorkCenterPerformance extends MetricValues {
  availability_target: Numeric;
  oee_on_target: boolean;
  oee_target: Numeric;
  parallel_capacity: number;
  performance_target: Numeric;
  quality_target: Numeric;
  work_center_code: string;
  work_center_id: number;
  work_center_name: string;
}

export interface PerformanceTrendPoint extends MetricValues {
  period_end: string;
  period_start: string;
}

export interface EquipmentReliability {
  availability_rate: Numeric;
  equipment_code: string;
  equipment_id: number;
  equipment_name: string;
  failure_count: number;
  last_failure_at?: string;
  mtbf_minutes?: NullableNumeric;
  mttr_minutes?: NullableNumeric;
  planned_downtime_minutes: Numeric;
  total_downtime_minutes: Numeric;
  unplanned_downtime_minutes: Numeric;
}

export interface CycleAnalysis {
  actual_cycle_seconds?: NullableNumeric;
  actual_run_minutes: Numeric;
  cycle_efficiency_rate: Numeric;
  execution_count: number;
  good_quantity: Numeric;
  ideal_cycle_seconds?: NullableNumeric;
  ideal_run_minutes: Numeric;
  operation_code: string;
  operation_id: number;
  operation_name: string;
  product_code: string;
  product_name: string;
  scrap_quantity: Numeric;
  total_quantity: Numeric;
  work_center_code: string;
  work_center_id: number;
  work_center_name: string;
}

export interface DowntimePareto {
  cumulative_percentage: Numeric;
  downtime_minutes: Numeric;
  event_count: number;
  percentage: Numeric;
  rank: number;
  reason: string;
}

export interface PerformanceTarget {
  availability_target: Numeric;
  configured: boolean;
  id?: number;
  ideal_cycle_seconds?: NullableNumeric;
  oee_target: Numeric;
  performance_target: Numeric;
  quality_target: Numeric;
  remark?: string;
  status: TargetStatus;
  work_center_code: string;
  work_center_id: number;
  work_center_name: string;
}

export interface PerformanceSnapshot extends MetricValues {
  calculated_at: string;
  id: number;
  metric_date: string;
  work_center_code: string;
  work_center_id: number;
  work_center_name: string;
}

export interface WorkCenterOption {
  code: string;
  id: number;
  name: string;
  production_enabled: boolean;
  status: string;
}

export const getPerformanceDashboardApi = (params?: PerformanceQuery) =>
  requestClient.get<PerformanceDashboard>(`${baseUrl}/dashboard`, { params });

export const getWorkCenterPerformanceApi = (params?: PerformanceQuery) =>
  requestClient.get<WorkCenterPerformance[]>(`${baseUrl}/work-centers`, { params });

export const getPerformanceTrendApi = (
  params?: PerformanceQuery & { grain?: MetricGrain },
) => requestClient.get<PerformanceTrendPoint[]>(`${baseUrl}/trend`, { params });

export const getEquipmentReliabilityApi = (
  params?: PerformanceQuery & { equipment_id?: number },
) => requestClient.get<EquipmentReliability[]>(`${baseUrl}/equipment-reliability`, { params });

export const getCycleAnalysisApi = (params?: PerformanceQuery) =>
  requestClient.get<CycleAnalysis[]>(`${baseUrl}/cycle-analysis`, { params });

export const getDowntimeParetoApi = (
  params?: PerformanceQuery & { top_n?: number },
) => requestClient.get<DowntimePareto[]>(`${baseUrl}/downtime-pareto`, { params });

export const getPerformanceTargetsApi = () =>
  requestClient.get<PerformanceTarget[]>(`${baseUrl}/targets`);

export const updatePerformanceTargetApi = (
  workCenterId: number,
  data: Recordable<any>,
) => requestClient.put<PerformanceTarget>(`${baseUrl}/targets/${workCenterId}`, data);

export const getPerformanceSnapshotsApi = (params?: PerformanceQuery) =>
  requestClient.get<PerformanceSnapshot[]>(`${baseUrl}/snapshots`, { params });

export const rebuildPerformanceSnapshotsApi = (data: Recordable<any>) =>
  requestClient.post<{
    end_date: string;
    snapshot_count: number;
    start_date: string;
    work_center_count: number;
  }>(`${baseUrl}/snapshots/rebuild`, data);

export const getPerformanceWorkCenterOptionsApi = () =>
  requestClient.get<WorkCenterOption[]>('/api/v1/mes/work-center/options');
