import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/bom';

export type BomStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE';

export interface BomMaterialSummary {
  id: number;
  code: string;
  name: string;
  specification?: string;
  model?: string;
  unit: string;
}

export interface BomItem {
  id: number;
  bom_id: number;
  line_no: number;
  component_material_id: number;
  quantity: number | string;
  unit_id: number;
  loss_rate: number | string;
  fixed_loss_qty: number | string;
  is_optional: boolean;
  remark?: string;
  sort_no: number;
  component: BomMaterialSummary;
  created_time: string;
  updated_time?: string;
}

export interface BomItemInput {
  line_no: number;
  component_material_id: number;
  quantity: number | string;
  unit_id?: number;
  loss_rate?: number | string;
  fixed_loss_qty?: number | string;
  is_optional?: boolean;
  remark?: string;
  sort_no?: number;
}

export interface BomItemRecord {
  id: number;
  bom_code: string;
  bom_version: string;
  product_material_id: number;
  status: BomStatus;
  base_quantity: number | string;
  effective_from?: string;
  effective_to?: string;
  is_default: boolean;
  remark?: string;
  product: BomMaterialSummary;
  items?: BomItem[];
  created_time: string;
  updated_time?: string;
}

export interface BomInput {
  bom_code: string;
  product_material_id: number;
  bom_version: string;
  base_quantity?: number | string;
  effective_from?: string;
  effective_to?: string;
  remark?: string;
}

export interface BomOption {
  id: number;
  bom_code: string;
  bom_version: string;
  status: BomStatus;
  effective_from?: string;
  effective_to?: string;
  is_default: boolean;
}

export interface BomTreeNode {
  material_id: number;
  material_code: string;
  material_name: string;
  specification?: string;
  quantity: number | string;
  unit: string;
  line_no?: number;
  loss_rate?: number | string;
  fixed_loss_qty?: number | string;
  is_optional: boolean;
  children: BomTreeNode[];
}

export interface BomTree {
  bom_id: number;
  bom_code: string;
  bom_version: string;
  material_id: number;
  material_code: string;
  material_name: string;
  quantity: number | string;
  unit: string;
  children: BomTreeNode[];
}

export interface BomValidationResult {
  valid: boolean;
  errors: string[];
}

export interface MaterialRequirement {
  material_id: number;
  material_code: string;
  material_name: string;
  standard_required_qty: number | string;
  loss_rate: number | string;
  fixed_loss_qty: number | string;
  planned_required_qty: number | string;
  unit: string;
  is_optional: boolean;
}

export interface BomCompareResult {
  source_bom_id: number;
  target_bom_id: number;
  changes: Array<{
    change_type: string;
    component_material_id: number;
    component_code: string;
    component_name: string;
    source_quantity?: number | string;
    target_quantity?: number | string;
    source_loss_rate?: number | string;
    target_loss_rate?: number | string;
  }>;
}

export function getBomListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<BomItemRecord>>(baseUrl, { params });
}

export function getBomApi(id: number) {
  return requestClient.get<BomItemRecord>(`${baseUrl}/${id}`);
}

export function createBomApi(data: BomInput) {
  return requestClient.post<BomItemRecord>(baseUrl, data);
}

export function updateBomApi(id: number, data: BomInput) {
  return requestClient.put<BomItemRecord>(`${baseUrl}/${id}`, data);
}

export function copyBomApi(id: number, data: Recordable<any>) {
  return requestClient.post<BomItemRecord>(`${baseUrl}/${id}/copy`, data);
}

export function validateBomApi(id: number) {
  return requestClient.post<BomValidationResult>(`${baseUrl}/${id}/validate`);
}

export function activateBomApi(id: number) {
  return requestClient.post<BomItemRecord>(`${baseUrl}/${id}/activate`);
}

export function deactivateBomApi(id: number) {
  return requestClient.post<BomItemRecord>(`${baseUrl}/${id}/deactivate`);
}

export function setDefaultBomApi(id: number) {
  return requestClient.put<BomItemRecord>(`${baseUrl}/${id}/default`);
}

export function getBomTreeApi(id: number) {
  return requestClient.get<BomTree>(`${baseUrl}/${id}/tree`);
}

export function calculateBomApi(id: number, data: Recordable<any>) {
  return requestClient.post<MaterialRequirement[]>(`${baseUrl}/${id}/calculate`, data);
}

export function createBomItemApi(bomId: number, data: BomItemInput) {
  return requestClient.post<BomItem>(`${baseUrl}/${bomId}/items`, data);
}

export function updateBomItemApi(bomId: number, itemId: number, data: BomItemInput) {
  return requestClient.put<BomItem>(`${baseUrl}/${bomId}/items/${itemId}`, data);
}

export function deleteBomItemApi(bomId: number, itemId: number) {
  return requestClient.delete(`${baseUrl}/${bomId}/items/${itemId}`);
}

export function compareBomApi(sourceBomId: number, targetBomId: number) {
  return requestClient.get<BomCompareResult>(`${baseUrl}/compare`, {
    params: { source_bom_id: sourceBomId, target_bom_id: targetBomId },
  });
}
