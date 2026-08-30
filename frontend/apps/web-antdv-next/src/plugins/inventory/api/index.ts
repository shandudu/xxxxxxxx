import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/inventory';

export interface InventoryBalance {
  id: number;
  material_id: number;
  lot_id?: number;
  warehouse_id: number;
  location_id: number;
  quantity: number;
  reserved_quantity: number;
  version: number;
  created_time: string;
  updated_time?: string;
}

export interface StockTransaction {
  id: number;
  transaction_no: string;
  transaction_type: string;
  material_id: number;
  lot_id?: number;
  warehouse_id: number;
  location_id: number;
  quantity_delta: number;
  balance_after: number;
  reference_type?: string;
  reference_no?: string;
  occurred_at: string;
}

export interface StockMovementLine {
  id?: number;
  line_no?: number;
  material_id: number;
  lot_id?: number;
  from_warehouse_id: number;
  from_location_id: number;
  to_warehouse_id: number;
  to_location_id: number;
  quantity: number;
  remark?: string;
}

export interface StockMovement {
  id: number;
  movement_no: string;
  status: 'CANCELLED' | 'DRAFT' | 'POSTED';
  remark?: string;
  posted_at?: string;
  lines: StockMovementLine[];
}

export interface InventoryPolicy {
  id: number;
  material_id: number;
  safety_stock: number;
  reorder_point: number;
  max_stock: number;
  min_order_quantity: number;
  purchase_lead_days: number;
  production_lead_days: number;
  review_period_days: number;
  status: string;
}

export interface ReplenishmentSuggestion {
  id: number;
  suggestion_no: string;
  material_id: number;
  evaluated_at: string;
  due_date: string;
  material_code_snapshot: string;
  material_name_snapshot: string;
  unit_code_snapshot: string;
  on_hand_quantity: number;
  reserved_quantity: number;
  open_purchase_quantity: number;
  open_production_quantity: number;
  demand_quantity: number;
  projected_available_quantity: number;
  safety_stock: number;
  reorder_point: number;
  suggested_quantity: number;
  order_type: 'PRODUCTION' | 'PURCHASE';
  alert_level: 'COVERED' | 'REORDER' | 'SHORTAGE';
  status: 'CANCELLED' | 'FIRM' | 'RELEASED' | 'SUGGESTED';
  source_document_no?: string;
}

export interface ReplenishmentDashboard {
  policy_count: number;
  suggestion_count: number;
  shortage_count: number;
  reorder_count: number;
  total_suggested_quantity: number;
  total_demand_quantity: number;
  purchase_suggestion_count: number;
  production_suggestion_count: number;
}

export interface ShelfLifeDashboard {
  policy_count: number;
  warning_count: number;
  critical_count: number;
  expired_count: number;
  open_hold_count: number;
  active_recall_count: number;
}

export interface ShelfLifePolicy {
  id: number;
  material_id: number;
  warning_days: number;
  critical_days: number;
  min_remaining_days_at_issue: number;
  fefo_enabled: boolean;
  auto_hold_expired: boolean;
  retest_required: boolean;
  status: string;
  remark?: string;
}

export interface ExpiryAlert {
  id: number;
  lot_id: number;
  level: 'CRITICAL' | 'EXPIRED' | 'WARNING';
  days_remaining: number;
  available_quantity: number;
  status: string;
  triggered_at: string;
}

export interface LotQualityHold {
  id: number;
  hold_no: string;
  lot_id: number;
  reason: string;
  status: string;
  inspection_id?: number;
  original_expiry_date?: string;
  new_expiry_date?: string;
  held_at: string;
  decision_reason?: string;
}

export interface FefoCandidate {
  balance_id: number;
  lot_id: number;
  lot_no: string;
  warehouse_id: number;
  location_id: number;
  expiry_date: string;
  days_remaining: number;
  available_quantity: number;
  allocated_quantity: number;
}

export interface LotRecallItem {
  id: number;
  item_type: string;
  status: string;
  quantity: number;
  lot_id?: number;
  shipment_id?: number;
  customer_id?: number;
  action_notes?: string;
}

export interface LotRecall {
  id: number;
  recall_no: string;
  root_lot_id: number;
  reason: string;
  severity: string;
  status: string;
  initiated_at: string;
  closed_at?: string;
  items: LotRecallItem[];
}

export function getInventoryBalancesApi(params?: Recordable<any>) {
  return requestClient.get<InventoryBalance[]>(`${baseUrl}/balances`, { params });
}

export function getStockTransactionsApi(params?: Recordable<any>) {
  return requestClient.get<StockTransaction[]>(`${baseUrl}/transactions`, { params });
}

export function createStockMovementApi(data: Recordable<any>) {
  return requestClient.post<StockMovement>(`${baseUrl}/movements`, data);
}

export function getStockMovementsApi(params?: Recordable<any>) {
  return requestClient.get<StockMovement[]>(`${baseUrl}/movements`, { params });
}

export function postStockMovementApi(id: number) {
  return requestClient.post<StockMovement>(`${baseUrl}/movements/${id}/post`);
}

export function postStockAdjustmentApi(data: Recordable<any>) {
  return requestClient.post<StockTransaction>(`${baseUrl}/adjustments`, data);
}

export function getInventoryPoliciesApi() {
  return requestClient.get<InventoryPolicy[]>(`${baseUrl}/policies`);
}
export function getReplenishmentDashboardApi() {
  return requestClient.get<ReplenishmentDashboard>(`${baseUrl}/replenishment/dashboard`);
}
export function getReplenishmentSuggestionsApi(params?: Recordable<any>) {
  return requestClient.get<ReplenishmentSuggestion[]>(`${baseUrl}/replenishment`, { params });
}
export function generateReplenishmentApi(data: Recordable<any> = {}) {
  return requestClient.post<ReplenishmentSuggestion[]>(`${baseUrl}/replenishment/generate`, data);
}
export function firmReplenishmentApi(id: number) {
  return requestClient.post<ReplenishmentSuggestion>(`${baseUrl}/replenishment/${id}/firm`);
}
export function releaseReplenishmentApi(id: number, data: Recordable<any>) {
  return requestClient.post<ReplenishmentSuggestion>(`${baseUrl}/replenishment/${id}/release`, data);
}

export function getShelfLifeDashboardApi() {
  return requestClient.get<ShelfLifeDashboard>(`${baseUrl}/shelf-life/dashboard`);
}
export function getShelfLifePoliciesApi() {
  return requestClient.get<ShelfLifePolicy[]>(`${baseUrl}/shelf-life/policies`);
}
export function upsertShelfLifePolicyApi(materialId: number, data: Recordable<any>) {
  return requestClient.put<ShelfLifePolicy>(`${baseUrl}/shelf-life/policies/${materialId}`, data);
}
export function syncExpiryAlertsApi() {
  return requestClient.post<ExpiryAlert[]>(`${baseUrl}/shelf-life/alerts/sync`);
}
export function getExpiryAlertsApi(params?: Recordable<any>) {
  return requestClient.get<ExpiryAlert[]>(`${baseUrl}/shelf-life/alerts`, { params });
}
export function acknowledgeExpiryAlertApi(id: number) {
  return requestClient.post<ExpiryAlert>(`${baseUrl}/shelf-life/alerts/${id}/acknowledge`);
}
export function getLotHoldsApi(params?: Recordable<any>) {
  return requestClient.get<LotQualityHold[]>(`${baseUrl}/shelf-life/holds`, { params });
}
export function createExpiryReinspectionApi(id: number) {
  return requestClient.post<LotQualityHold>(`${baseUrl}/shelf-life/holds/${id}/reinspect`);
}
export function releaseLotHoldApi(id: number, data: Recordable<any>) {
  return requestClient.post<LotQualityHold>(`${baseUrl}/shelf-life/holds/${id}/release`, data);
}
export function scrapLotHoldApi(id: number, data: Recordable<any>) {
  return requestClient.post<LotQualityHold>(`${baseUrl}/shelf-life/holds/${id}/scrap`, data);
}
export function getFefoCandidatesApi(params: Recordable<any>) {
  return requestClient.get<FefoCandidate[]>(`${baseUrl}/shelf-life/fefo-candidates`, { params });
}
export function getLotRecallsApi(params?: Recordable<any>) {
  return requestClient.get<LotRecall[]>(`${baseUrl}/recalls`, { params });
}
export function createLotRecallApi(data: Recordable<any>) {
  return requestClient.post<LotRecall>(`${baseUrl}/recalls`, data);
}
export function updateLotRecallItemApi(recallId: number, itemId: number, data: Recordable<any>) {
  return requestClient.put<LotRecallItem>(`${baseUrl}/recalls/${recallId}/items/${itemId}`, data);
}
export function closeLotRecallApi(id: number) {
  return requestClient.post<LotRecall>(`${baseUrl}/recalls/${id}/close`);
}
