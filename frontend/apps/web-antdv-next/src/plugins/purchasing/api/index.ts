import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/erp/purchasing';

export interface PurchaseOrderLine {
  id: number;
  line_no: number;
  material_id: number;
  ordered_quantity: number;
  received_quantity: number;
  unit_price?: number;
  material_code_snapshot: string;
  material_name_snapshot: string;
  unit_code_snapshot: string;
  requested_delivery_at?: string;
  supplier_confirmed_delivery_at?: string;
}

export interface PurchaseOrder {
  id: number;
  purchase_order_no: string;
  supplier_id: number;
  supplier_code_snapshot: string;
  supplier_name_snapshot: string;
  status: 'CANCELLED' | 'CONFIRMED' | 'DRAFT' | 'PARTIALLY_RECEIVED' | 'RECEIVED';
  currency: string;
  remark?: string;
  created_time: string;
  lines: PurchaseOrderLine[];
}

export interface SupplierReceipt {
  id: number;
  receipt_no: string;
  purchase_order_id: number;
  supplier_id: number;
  supplier_name_snapshot: string;
  status: 'POSTED';
  created_time: string;
}

export interface SupplierReturn {
  id: number;
  return_no: string;
  supplier_id: number;
  supplier_receipt_id: number;
  ncr_id: number;
  disposition_id: number;
  supplier_name_snapshot: string;
  status: string;
  created_time: string;
}

export interface SupplierOption {
  id: number;
  code: string;
  name: string;
}

export function getPurchaseOrdersApi(params?: Recordable<any>) {
  return requestClient.get<PurchaseOrder[]>(`${baseUrl}/orders`, { params });
}

export function getPurchaseOrderApi(id: number) {
  return requestClient.get<PurchaseOrder>(`${baseUrl}/orders/${id}`);
}

export function createPurchaseOrderApi(data: Recordable<any>) {
  return requestClient.post<PurchaseOrder>(`${baseUrl}/orders`, data);
}

export function confirmPurchaseOrderApi(id: number, data?: Recordable<any>) {
  return requestClient.post<PurchaseOrder>(`${baseUrl}/orders/${id}/confirm`, data ?? {});
}

export function cancelPurchaseOrderApi(id: number) {
  return requestClient.post<PurchaseOrder>(`${baseUrl}/orders/${id}/cancel`);
}

export function getSupplierReceiptsApi(params?: Recordable<any>) {
  return requestClient.get<SupplierReceipt[]>(`${baseUrl}/receipts`, { params });
}

export function createSupplierReceiptApi(data: Recordable<any>) {
  return requestClient.post<SupplierReceipt>(`${baseUrl}/receipts`, data);
}

export function getSupplierReturnsApi() {
  return requestClient.get<SupplierReturn[]>(`${baseUrl}/returns`);
}

export function getPurchasingSupplierOptionsApi() {
  return requestClient.get<SupplierOption[]>('/api/v1/erp/supplier/options');
}

export interface PurchaseDeliveryPerformance {
  id: number;
  supplier_id: number;
  purchase_order_id: number;
  purchase_order_line_id: number;
  material_id: number;
  requested_delivery_at: string;
  supplier_confirmed_delivery_at?: string;
  effective_delivery_at: string;
  assessed_at: string;
  ordered_quantity: number;
  actual_delivery_at?: string;
  received_quantity: number;
  on_time: boolean;
  in_full: boolean;
  otif_status: string;
  delay_reason?: string;
  days_late: number;
  shortage_impact_quantity: number;
  impacted_sales_order_count: number;
  mrp_uncovered_quantity: number;
}

export interface PurchaseDeliveryDashboard {
  order_count: number;
  supplier_count: number;
  line_count: number;
  otif_line_count: number;
  delayed_line_count: number;
  otif_rate: number;
  delayed_quantity: number;
  shortage_impact_quantity: number;
  impacted_sales_order_count: number;
  supplier_otif: Array<{ supplier_id: number; line_count: number; otif_line_count: number; otif_rate: number }>;
}

export function getPurchaseDeliveryDashboardApi() {
  return requestClient.get<PurchaseDeliveryDashboard>(`${baseUrl}/delivery/dashboard`);
}
export function recalculatePurchaseDeliveryApi() {
  return requestClient.post<{ assessed_order_count: number; assessed_line_count: number; assessed_at: string }>(`${baseUrl}/delivery/recalculate`);
}
export function getPurchaseOrderDeliveryPerformanceApi(id: number) {
  return requestClient.get<PurchaseDeliveryPerformance[]>(`${baseUrl}/orders/${id}/delivery-performance`);
}
