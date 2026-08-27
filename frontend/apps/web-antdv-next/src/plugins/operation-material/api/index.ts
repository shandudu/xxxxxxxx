import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/operation-material-plans';

export type PlanStatus = 'ACTIVE' | 'DRAFT' | 'INACTIVE';

export interface OperationMaterialRequirement {
  id: number;
  plan_id: number;
  bom_item_id: number;
  routing_operation_id: number;
  quantity: number;
  remark?: string;
}

export interface OperationMaterialPlan {
  id: number;
  plan_code: string;
  bom_id: number;
  routing_id: number;
  status: PlanStatus;
  remark?: string;
  created_time: string;
  requirements: OperationMaterialRequirement[];
}

export interface PlanValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  bom_item_count: number;
  allocated_item_count: number;
}

export const getPlansApi = () =>
  requestClient.get<OperationMaterialPlan[]>(baseUrl);
export const getPlanApi = (id: number) =>
  requestClient.get<OperationMaterialPlan>(`${baseUrl}/${id}`);
export const createPlanApi = (data: Recordable<any>) =>
  requestClient.post<OperationMaterialPlan>(baseUrl, data);
export const addRequirementApi = (planId: number, data: Recordable<any>) =>
  requestClient.post<OperationMaterialRequirement>(`${baseUrl}/${planId}/requirements`, data);
export const updateRequirementApi = (planId: number, id: number, data: Recordable<any>) =>
  requestClient.put<OperationMaterialRequirement>(`${baseUrl}/${planId}/requirements/${id}`, data);
export const deleteRequirementApi = (planId: number, id: number) =>
  requestClient.delete(`${baseUrl}/${planId}/requirements/${id}`);
export const validatePlanApi = (id: number) =>
  requestClient.post<PlanValidation>(`${baseUrl}/${id}/validate`);
export const activatePlanApi = (id: number) =>
  requestClient.post<OperationMaterialPlan>(`${baseUrl}/${id}/activate`);
export const deactivatePlanApi = (id: number) =>
  requestClient.post<OperationMaterialPlan>(`${baseUrl}/${id}/deactivate`);
