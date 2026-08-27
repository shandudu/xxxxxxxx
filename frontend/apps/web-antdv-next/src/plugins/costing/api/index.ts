import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/erp/costing';
export type Numeric = number | string;
export type MarginDimension = 'PRODUCT' | 'CUSTOMER';
export interface CostPeriod { id:number; period_code:string; start_date:string; end_date:string; status:string; labor_rate_per_hour:Numeric; machine_rate_per_hour:Numeric; overhead_rate_per_hour:Numeric; }
export interface CostLine { id:number; element:string; description:string; quantity:Numeric; unit_rate:Numeric; amount:Numeric; }
export interface WorkOrderCost { id:number; work_order_id:number; work_order_no_snapshot:string; product_code_snapshot:string; product_name_snapshot:string; good_quantity:Numeric; scrap_quantity:Numeric; material_cost:Numeric; labor_cost:Numeric; machine_cost:Numeric; overhead_cost:Numeric; quality_loss_cost:Numeric; total_cost:Numeric; unit_cost:Numeric; status:string; lines:CostLine[]; }
export interface MarginRow { dimension:MarginDimension; key:string; name:string; shipped_quantity:Numeric; revenue:Numeric; cogs:Numeric; gross_profit:Numeric; margin_rate:Numeric; cost_coverage:Numeric; }
export interface MarginDashboard { period_id?:number; period_code?:string; dimension:MarginDimension; rows:MarginRow[]; revenue:Numeric; cogs:Numeric; gross_profit:Numeric; margin_rate:Numeric; }
export const getCostPeriodsApi = () => requestClient.get<CostPeriod[]>(`${baseUrl}/periods`);
export const createCostPeriodApi = (data:Record<string,any>) => requestClient.post<CostPeriod>(`${baseUrl}/periods`, data);
export const getWorkOrderCostApi = (workOrderId:number, periodId:number) => requestClient.get<WorkOrderCost>(`${baseUrl}/work-orders/${workOrderId}`, { params:{period_id:periodId} });
export const calculateWorkOrderCostApi = (workOrderId:number, periodId:number) => requestClient.post<WorkOrderCost>(`${baseUrl}/work-orders/${workOrderId}/calculate`, {period_id:periodId});
export const postWorkOrderCostApi = (workOrderId:number, periodId:number) => requestClient.post<WorkOrderCost>(`${baseUrl}/work-orders/${workOrderId}/post`, {period_id:periodId});
export const getMarginDashboardApi = (dimension:MarginDimension, periodId?:number) => requestClient.get<MarginDashboard>(`${baseUrl}/margins`, {params:{dimension, period_id:periodId}});
