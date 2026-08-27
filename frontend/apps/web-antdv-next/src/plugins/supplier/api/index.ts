import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/erp/supplier';

export type SupplierStatus = 'ACTIVE' | 'DISABLED';
export type CooperationStatus = 'NORMAL' | 'SUSPENDED' | 'BLACKLISTED';
export type QualityStatus = 'QUALIFIED' | 'CONDITIONAL' | 'UNQUALIFIED' | 'PENDING';
export type SupplierMaterialStatus = 'ACTIVE' | 'SUSPENDED' | 'DISABLED';

export interface SupplierCategory {
  id: number;
  category_code: string;
  category_name: string;
  parent_id?: number;
  status: SupplierStatus;
  sort_no: number;
  remark?: string;
}

export interface SupplierCategoryTreeNode {
  id: number;
  code: string;
  name: string;
  parent_id?: number;
  status: SupplierStatus;
  sort_no: number;
  children: SupplierCategoryTreeNode[];
}

export interface SupplierItem {
  id: number;
  supplier_code: string;
  supplier_name: string;
  short_name?: string;
  category_id: number;
  category_name?: string;
  supplier_type: string;
  company_type: string;
  status: SupplierStatus;
  cooperation_status: CooperationStatus;
  quality_status: QualityStatus;
  purchasing_enabled: boolean;
  quality_enabled: boolean;
  trace_enabled: boolean;
  preferred: boolean;
  currency: string;
  payment_terms?: string;
  default_lead_time_days?: number;
  unified_social_credit_code?: string;
  tax_number?: string;
  registered_address?: string;
  business_address?: string;
  website?: string;
  country?: string;
  province?: string;
  city?: string;
  remark?: string;
  created_time: string;
  updated_time?: string;
}

export interface SupplierOption {
  id: number;
  code: string;
  name: string;
  short_name?: string;
  category_id: number;
  preferred: boolean;
}

export interface SupplierContact {
  id: number;
  supplier_id: number;
  contact_name: string;
  contact_type: string;
  department?: string;
  position?: string;
  mobile?: string;
  telephone?: string;
  email?: string;
  wechat?: string;
  is_primary: boolean;
  status: SupplierStatus;
  remark?: string;
}

export interface SupplierMaterial {
  id: number;
  supplier_id: number;
  material_id: number;
  material_code?: string;
  material_name?: string;
  material_specification?: string;
  unit?: string;
  supplier_material_code?: string;
  supplier_material_name?: string;
  status: SupplierMaterialStatus;
  preferred: boolean;
  minimum_order_quantity?: number;
  lead_time_days?: number;
  quality_inspection_required: boolean;
  remark?: string;
}

export type SupplierForm = Omit<
  SupplierItem,
  'category_name' | 'created_time' | 'id' | 'updated_time'
> & { id?: number };

export type SupplierContactForm = Omit<
  SupplierContact,
  'id' | 'supplier_id'
> & { id?: number };

export type SupplierMaterialForm = Omit<
  SupplierMaterial,
  | 'id'
  | 'material_code'
  | 'material_name'
  | 'material_specification'
  | 'supplier_id'
  | 'unit'
> & { id?: number };

export function getSupplierCategoryTreeApi() {
  return requestClient.get<SupplierCategoryTreeNode[]>(`${baseUrl}/category/tree`);
}

export function createSupplierCategoryApi(data: Recordable<any>) {
  return requestClient.post<SupplierCategory>(`${baseUrl}/category`, data);
}

export function updateSupplierCategoryApi(id: number, data: Recordable<any>) {
  return requestClient.put<SupplierCategory>(`${baseUrl}/category/${id}`, data);
}

export function updateSupplierCategoryStatusApi(id: number, status: SupplierStatus) {
  return requestClient.put<SupplierCategory>(`${baseUrl}/category/${id}/status`, { status });
}

export function getSupplierListApi(params?: Recordable<any>) {
  return requestClient.get<PaginationResult<SupplierItem>>(baseUrl, { params });
}

export function getSupplierApi(id: number) {
  return requestClient.get<SupplierItem>(`${baseUrl}/${id}`);
}

export function createSupplierApi(data: SupplierForm) {
  return requestClient.post<SupplierItem>(baseUrl, data);
}

export function updateSupplierApi(id: number, data: SupplierForm) {
  return requestClient.put<SupplierItem>(`${baseUrl}/${id}`, data);
}

export function updateSupplierStatusApi(id: number, status: SupplierStatus) {
  return requestClient.put<SupplierItem>(`${baseUrl}/${id}/status`, { status });
}

export function updateSupplierCooperationApi(id: number, cooperation_status: CooperationStatus) {
  return requestClient.put<SupplierItem>(`${baseUrl}/${id}/cooperation`, { cooperation_status });
}

export function updateSupplierQualityApi(id: number, quality_status: QualityStatus) {
  return requestClient.put<SupplierItem>(`${baseUrl}/${id}/quality`, { quality_status });
}

export function getSupplierContactsApi(supplierId: number) {
  return requestClient.get<SupplierContact[]>(`${baseUrl}/${supplierId}/contacts`);
}

export function createSupplierContactApi(supplierId: number, data: SupplierContactForm) {
  return requestClient.post<SupplierContact>(`${baseUrl}/${supplierId}/contacts`, data);
}

export function updateSupplierContactApi(contactId: number, data: SupplierContactForm) {
  return requestClient.put<SupplierContact>(`${baseUrl}/contacts/${contactId}`, data);
}

export function setSupplierContactPrimaryApi(contactId: number) {
  return requestClient.put<SupplierContact>(`${baseUrl}/contacts/${contactId}/primary`);
}

export function updateSupplierContactStatusApi(contactId: number, status: SupplierStatus) {
  return requestClient.put<SupplierContact>(`${baseUrl}/contacts/${contactId}/status`, { status });
}

export function getSupplierMaterialsApi(supplierId: number) {
  return requestClient.get<SupplierMaterial[]>(`${baseUrl}/${supplierId}/materials`);
}

export function createSupplierMaterialApi(supplierId: number, data: SupplierMaterialForm) {
  return requestClient.post<SupplierMaterial>(`${baseUrl}/${supplierId}/materials`, data);
}

export function updateSupplierMaterialApi(relationId: number, data: SupplierMaterialForm) {
  return requestClient.put<SupplierMaterial>(`${baseUrl}/materials/${relationId}`, data);
}

export function updateSupplierMaterialStatusApi(relationId: number, status: SupplierMaterialStatus) {
  return requestClient.put<SupplierMaterial>(`${baseUrl}/materials/${relationId}/status`, { status });
}
