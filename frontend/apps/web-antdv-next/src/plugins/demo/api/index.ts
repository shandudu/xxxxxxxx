import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/demo/manufacturing-happy-path';

export interface ManufacturingDemoRun {
  completed_at?: string;
  error_message?: string;
  failed_step?: string;
  id: number;
  run_no: string;
  scenario_code: string;
  started_at: string;
  status: 'COMPLETED' | 'FAILED' | 'RUNNING';
}

export interface ManufacturingDemoVerifyResult {
  completed_steps: string[];
  missing_steps: string[];
  passed: boolean;
  references: Record<string, string>;
}

export interface ManufacturingDemoStatus {
  run?: ManufacturingDemoRun;
  verification: ManufacturingDemoVerifyResult;
}

export const getManufacturingDemoStatusApi = () =>
  requestClient.get<ManufacturingDemoStatus>(`${baseUrl}/status`);

export const runManufacturingDemoApi = () =>
  requestClient.post<ManufacturingDemoRun>(`${baseUrl}/run`);

export const verifyManufacturingDemoApi = () =>
  requestClient.post<ManufacturingDemoVerifyResult>(`${baseUrl}/verify`);
