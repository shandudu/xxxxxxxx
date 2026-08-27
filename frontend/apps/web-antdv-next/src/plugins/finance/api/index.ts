import { requestClient } from '#/api/request';
const baseUrl = '/api/v1/erp/finance';
export type Numeric = number | string;
export interface FinancePeriod { id:number; period_code:string; start_date:string; end_date:string; status:string; }
export interface FinanceDashboard { period_id?:number; period_code?:string; inventory_value:Numeric; accounts_receivable:Numeric; overdue_receivable:Numeric; accounts_payable:Numeric; overdue_payable:Numeric; revenue:Numeric; cogs:Numeric; gross_profit:Numeric; gross_margin_rate:Numeric; cash_in:Numeric; cash_out:Numeric; voucher_count:number; }
export interface InventoryValuation { id:number; material_code_snapshot:string; material_name_snapshot:string; opening_quantity:Numeric; receipt_quantity:Numeric; issue_quantity:Numeric; closing_quantity:Numeric; closing_value:Numeric; unit_cost:Numeric; coverage_rate:Numeric; }
export interface PaymentPlan { id:number; plan_no:string; direction:string; partner_name_snapshot:string; due_date:string; planned_amount:Numeric; settled_amount:Numeric; status:string; }
export interface BankStatement { id:number; statement_no:string; bank_account:string; transaction_date:string; direction:string; amount:Numeric; counterparty_name?:string; reference_no?:string; status:string; }
export interface ClosingCheck { id:number; check_code:string; check_name:string; status:string; blocking:boolean; detail?:string; }
export interface CashFlowForecast { period_id:number; inflow:Numeric; outflow:Numeric; net_cash_flow:Numeric; rows:any[]; }
export interface Budget { id:number; budget_no:string; budget_name:string; total_amount:Numeric; status:string; lines:any[]; }
export interface BudgetAlert { id:number; alert_type:string; threshold:Numeric; budget_amount:Numeric; consumed_amount:Numeric; utilization_rate:Numeric; status:string; detail?:string; }
export interface FixedAsset { id:number; asset_no:string; asset_name:string; category:string; original_value:Numeric; accumulated_depreciation:Numeric; net_value:Numeric; status:string; useful_life_months:number; barcode?:string; serial_number?:string; cost_center_id?:number; }
export interface FixedAssetCountLine { id:number; task_id:number; asset_id:number; barcode_snapshot?:string; serial_snapshot?:string; counted:boolean; observed_cost_center_id?:number; variance_type:string; remark?:string; evidence_photo?:string; evidence_note?:string; approval_status:string; approved_by?:number; approved_at?:string; }
export interface FixedAssetCount { id:number; task_no:string; period_id:number; status:string; zone_code?:string; assigned_user_id?:number; counted_at?:string; posted_at?:string; remark?:string; lines:FixedAssetCountLine[]; }
export interface FixedAssetCountScanResult { task_id:number; asset:FixedAsset; line:FixedAssetCountLine; is_new:boolean; }
export const getFinancePeriodsApi=()=>requestClient.get<FinancePeriod[]>(`${baseUrl}/periods`);
export const getFinanceDashboardApi=(periodId?:number)=>requestClient.get<FinanceDashboard>(`${baseUrl}/dashboard`,{params:{period_id:periodId}});
export const calculateInventoryValuationApi=(periodId:number)=>requestClient.post<InventoryValuation[]>(`${baseUrl}/inventory/valuation/calculate`,null,{params:{period_id:periodId}});
export const getPaymentPlansApi=()=>requestClient.get<PaymentPlan[]>(`${baseUrl}/payment-plans`);
export const getBankStatementsApi=()=>requestClient.get<BankStatement[]>(`${baseUrl}/bank/statements`);
export const autoReconcileBankStatementApi=(statementId:number)=>requestClient.post<BankStatement>(`${baseUrl}/bank/statements/${statementId}/auto-reconcile`);
export const autoArInvoiceApi=(shipmentId:number,data:Record<string,any>)=>requestClient.post(`${baseUrl}/ar/invoices/from-shipments/${shipmentId}`,data);
export const autoApInvoiceApi=(receiptId:number,data:Record<string,any>)=>requestClient.post(`${baseUrl}/ap/invoices/from-receipts/${receiptId}`,data);
export const runClosingCheckApi=(periodId:number)=>requestClient.post<ClosingCheck[]>(`${baseUrl}/periods/${periodId}/closing/check`);
export const closeFinancePeriodApi=(periodId:number)=>requestClient.post(`${baseUrl}/periods/${periodId}/closing/close`);
export const syncTaxInvoicesApi=(periodId:number)=>requestClient.post(`${baseUrl}/tax/invoices/sync`,{period_id:periodId});
export const rebuildCashFlowForecastApi=(periodId:number)=>requestClient.post<CashFlowForecast>(`${baseUrl}/cash-flow/forecast/rebuild`,null,{params:{period_id:periodId}});
export const getBudgetsApi=(periodId?:number)=>requestClient.get<Budget[]>(`${baseUrl}/budgets`,{params:{period_id:periodId}});
export const approveBudgetApi=(budgetId:number)=>requestClient.post<Budget>(`${baseUrl}/budgets/${budgetId}/approve`);
export const getBudgetAlertsApi=(periodId?:number)=>requestClient.get<BudgetAlert[]>(`${baseUrl}/budget-alerts`,{params:{period_id:periodId}});
export const createExpenseClaimApi=(data:Record<string,any>)=>requestClient.post(`${baseUrl}/expenses`,data);
export const approveExpenseClaimApi=(claimId:number)=>requestClient.post(`${baseUrl}/expenses/${claimId}/approve`);
export const getFixedAssetsApi=()=>requestClient.get<FixedAsset[]>(`${baseUrl}/fixed-assets`);
export const runFixedAssetDepreciationApi=(periodId:number)=>requestClient.post(`${baseUrl}/fixed-assets/depreciation/run`,null,{params:{period_id:periodId}});
export const runFixedAssetDualDepreciationApi=(periodId:number)=>requestClient.post(`${baseUrl}/fixed-assets/depreciation/dual-run`,null,{params:{period_id:periodId}});
export const createFixedAssetCountApi=(data:Record<string,any>)=>requestClient.post(`${baseUrl}/fixed-assets/counts`,data);
export const getFixedAssetCountApi=(taskId:number)=>requestClient.get<FixedAssetCount>(`${baseUrl}/fixed-assets/counts/${taskId}`);
export const scanFixedAssetCountApi=(taskId:number,data:{code:string; counted?:boolean; observed_cost_center_id?:number; variance_type?:string; remark?:string; evidence_photo?:string; evidence_note?:string})=>requestClient.post<FixedAssetCountScanResult>(`${baseUrl}/fixed-assets/counts/${taskId}/scan`,data);
export const approveFixedAssetCountLineApi=(taskId:number,lineId:number,data:{status:'APPROVED'|'REJECTED'; evidence_photo?:string; evidence_note?:string})=>requestClient.post<FixedAssetCountLine>(`${baseUrl}/fixed-assets/counts/${taskId}/lines/${lineId}/approval`,data);
export const postFixedAssetCountApi=(taskId:number)=>requestClient.post<FixedAssetCount>(`${baseUrl}/fixed-assets/counts/${taskId}/post`);
export const lookupFixedAssetApi=(code:string)=>requestClient.get<FixedAsset>(`${baseUrl}/fixed-assets/lookup`,{params:{code}});
export const createFixedAssetFromReceiptApi=(receiptId:number,data:Record<string,any>)=>requestClient.post<FixedAsset>(`${baseUrl}/fixed-assets/from-receipts/${receiptId}`,data);
