import type { Recordable } from '@vben/types';
import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/production';

export interface WorkOrderOperation { id: number; sequence_no: number; operation_code_snapshot: string; operation_name_snapshot: string; status: string; completed_quantity: number; }
export interface WorkOrderRequirement { id: number; line_no: number; material_id: number; material_code_snapshot: string; material_name_snapshot: string; required_quantity: number; issued_quantity: number; returned_quantity: number; }
export interface WorkOrder { id: number; work_order_no: string; product_material_id: number; product_code_snapshot: string; product_name_snapshot: string; planned_quantity: number; completed_quantity: number; scrap_quantity: number; status: 'CANCELLED'|'COMPLETED'|'DRAFT'|'IN_PROGRESS'|'RELEASED'; bom_id: number; bom_code_snapshot: string; bom_version_snapshot: string; routing_id: number; routing_code_snapshot: string; routing_version_snapshot: string; created_time: string; operations: WorkOrderOperation[]; requirements: WorkOrderRequirement[]; }
export interface MaterialIssueLine { id: number; requirement_id: number; material_id: number; lot_id?: number; warehouse_id: number; location_id: number; quantity: number; returned_quantity: number; }
export interface MaterialIssue { id: number; issue_no: string; work_order_id: number; status: string; lines: MaterialIssueLine[]; }
export interface VersionOption { id: number; code?: string; name?: string; bom_code?: string; bom_version?: string; routing_version?: string; }
export interface ProductionDashboard { total_orders:number; draft_orders:number; released_orders:number; in_progress_orders:number; completed_orders:number; planned_quantity:number; completed_quantity:number; completion_rate:number; }
export interface MaterialVariance { requirement_id:number; material_code:string; material_name:string; required_quantity:number; actual_quantity:number; variance_quantity:number; variance_rate?:number; }
export interface MaterialConsumption { id:number; consumption_no:string; execution_id:number; requirement_id:number; issue_line_id?:number; material_id:number; lot_id?:number; quantity:number; consumed_at:string; remark?:string; }
export interface ProductionExecution { id:number; execution_no:string; work_order_id:number; work_order_operation_id:number; status:'CANCELLED'|'COMPLETED'|'IN_PROGRESS'; good_quantity:number; scrap_quantity:number; started_at:string; completed_at?:string; remark?:string; consumptions:MaterialConsumption[]; }
export interface AndonEvent { id:number; event_no:string; event_type:'STOPPAGE'|'MATERIAL_SHORTAGE'|'QUALITY'; priority:'LOW'|'MEDIUM'|'HIGH'|'CRITICAL'; status:'OPEN'|'ACKNOWLEDGED'|'IN_PROGRESS'|'BLOCKED'|'RESOLVED'|'CANCELLED'; title:string; description:string; work_order_id?:number; work_order_operation_id?:number; equipment_id?:number; material_id?:number; ncr_id?:number; assignee_id?:number; occurred_at:string; sla_due_at:string; acknowledged_at?:string; started_at?:string; resolved_at?:string; escalation_level:number; root_cause?:string; resolution_notes?:string; created_time:string; }
export interface AndonDashboard { status_counts:Record<string,number>; type_counts:Record<string,number>; priority_counts:Record<string,number>; active_count:number; overdue_count:number; average_resolve_hours:number; }

export const getWorkOrdersApi = (params?: Recordable<any>) => requestClient.get<WorkOrder[]>(`${baseUrl}/work-orders`, { params });
export const getProductionDashboardApi = () => requestClient.get<ProductionDashboard>(`${baseUrl}/dashboard`);
export const getMaterialVarianceApi = (id:number) => requestClient.get<MaterialVariance[]>(`${baseUrl}/work-orders/${id}/material-variance`);
export const getExecutionsApi = (id:number) => requestClient.get<ProductionExecution[]>(`${baseUrl}/work-orders/${id}/executions`);
export const startExecutionApi = (orderId:number, operationId:number, data:Recordable<any>={}) => requestClient.post<ProductionExecution>(`${baseUrl}/work-orders/${orderId}/operations/${operationId}/executions/start`,data);
export const recordConsumptionApi = (executionId:number,data:Recordable<any>) => requestClient.post<MaterialConsumption>(`${baseUrl}/executions/${executionId}/consumptions`,data);
export const completeExecutionApi = (executionId:number,data:Recordable<any>) => requestClient.post<ProductionExecution>(`${baseUrl}/executions/${executionId}/complete`,data);
export const getWorkOrderApi = (id: number) => requestClient.get<WorkOrder>(`${baseUrl}/work-orders/${id}`);
export const createWorkOrderApi = (data: Recordable<any>) => requestClient.post<WorkOrder>(`${baseUrl}/work-orders`, data);
export const releaseWorkOrderApi = (id: number) => requestClient.post<WorkOrder>(`${baseUrl}/work-orders/${id}/release`);
export const startWorkOrderApi = (id: number) => requestClient.post<WorkOrder>(`${baseUrl}/work-orders/${id}/start`);
export const getMaterialIssuesApi = (id: number) => requestClient.get<MaterialIssue[]>(`${baseUrl}/work-orders/${id}/material-issues`);
export const issueMaterialApi = (data: Recordable<any>) => requestClient.post<MaterialIssue>(`${baseUrl}/material-issues`, data);
export const returnMaterialApi = (data: Recordable<any>) => requestClient.post(`${baseUrl}/material-returns`, data);
export const reportProductionApi = (data: Recordable<any>) => requestClient.post(`${baseUrl}/reports`, data);
export const getBomVersionOptionsApi = (product_material_id: number) => requestClient.get<VersionOption[]>('/api/v1/mes/bom/options', { params: { product_material_id } });
export const getRoutingVersionOptionsApi = (product_material_id: number) => requestClient.get<VersionOption[]>('/api/v1/mes/routing/options', { params: { product_material_id } });
export const getAndonDashboardApi = () => requestClient.get<AndonDashboard>(`${baseUrl}/andon/dashboard`);
export const getAndonEventsApi = (params?: Recordable<any>) => requestClient.get<AndonEvent[]>(`${baseUrl}/andon/events`, { params });
export const createAndonEventApi = (data: Recordable<any>) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events`, data);
export const assignAndonEventApi = (id:number, data:Recordable<any>) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events/${id}/assign`, data);
export const startAndonEventApi = (id:number) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events/${id}/start`);
export const resolveAndonEventApi = (id:number, data:Recordable<any>) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events/${id}/resolve`, data);
export const escalateAndonEventApi = (id:number, notes?:string) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events/${id}/escalate${notes ? `?notes=${encodeURIComponent(notes)}` : ''}`);
export const cancelAndonEventApi = (id:number) => requestClient.post<AndonEvent>(`${baseUrl}/andon/events/${id}/cancel`);
