import type { Recordable } from '@vben/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/mes/shopfloor';

export type ShopfloorStatus = 'ACTIVE' | 'DISABLED';

export interface UserOption { id: number; nickname: string; username: string }
export interface WorkCenterOption { code: string; id: number; name: string }
export interface EquipmentOption { code: string; id: number; name: string }
export interface TeamMember { id: number; member_role: string; nickname: string; status: ShopfloorStatus; user_id: number; username: string }
export interface Team { created_time: string; id: number; leader_user_id?: number; leader_username?: string; members: TeamMember[]; remark?: string; status: ShopfloorStatus; team_code: string; team_name: string; work_center_code?: string; work_center_id?: number; work_center_name?: string }
export interface Workstation { created_time: string; equipment_code?: string; equipment_id?: number; equipment_name?: string; id: number; remark?: string; status: ShopfloorStatus; terminal_enabled: boolean; work_center_code: string; work_center_id: number; work_center_name: string; workstation_code: string; workstation_name: string }
export interface Session { id: number; signed_in_at: string; signed_out_at?: string; status: 'ACTIVE' | 'CLOSED'; team_id?: number; user_id: number; workstation_id: number }
export interface TerminalDispatch { dispatch_no: string; dispatch_quantity: number | string; id: number; operation_name: string; planned_end_at: string; planned_start_at: string; production_execution_id?: number; status: string; work_order_no: string }
export interface TerminalContext { dispatches: TerminalDispatch[]; session?: Session; workstation: Workstation }

export const getTeamsApi = () => requestClient.get<Team[]>(`${baseUrl}/teams`);
export const createTeamApi = (data: Recordable<any>) => requestClient.post<Team>(`${baseUrl}/teams`, data);
export const updateTeamApi = (id: number, data: Recordable<any>) => requestClient.put<Team>(`${baseUrl}/teams/${id}`, data);
export const addTeamMemberApi = (id: number, data: Recordable<any>) => requestClient.post<Team>(`${baseUrl}/teams/${id}/members`, data);
export const getWorkstationsApi = () => requestClient.get<Workstation[]>(`${baseUrl}/workstations`);
export const createWorkstationApi = (data: Recordable<any>) => requestClient.post<Workstation>(`${baseUrl}/workstations`, data);
export const updateWorkstationApi = (id: number, data: Recordable<any>) => requestClient.put<Workstation>(`${baseUrl}/workstations/${id}`, data);
export const getWorkstationOptionsApi = () => requestClient.get<{ code: string; id: number; name: string; work_center_id: number }[]>(`${baseUrl}/workstations/options`);
export const getUserOptionsApi = () => requestClient.get<UserOption[]>(`${baseUrl}/users/options`);
export const getTerminalContextApi = (id: number) => requestClient.get<TerminalContext>(`${baseUrl}/terminal/${id}/context`);
export const checkInApi = (id: number, data: Recordable<any>) => requestClient.post<Session>(`${baseUrl}/terminal/${id}/check-in`, data);
export const checkOutApi = (id: number) => requestClient.post<Session>(`${baseUrl}/terminal/sessions/${id}/check-out`);
export const startDispatchApi = (stationId: number, dispatchId: number) => requestClient.post<TerminalDispatch>(`${baseUrl}/terminal/${stationId}/dispatches/${dispatchId}/start`);
export const completeDispatchApi = (stationId: number, dispatchId: number, data: Recordable<any>) => requestClient.post<TerminalDispatch>(`${baseUrl}/terminal/${stationId}/dispatches/${dispatchId}/complete`, data);
export const getWorkCenterOptionsApi = () => requestClient.get<WorkCenterOption[]>('/api/v1/mes/work-center/options');
export const getEquipmentOptionsApi = () => requestClient.get<EquipmentOption[]>('/api/v1/mes/equipment/options', { params: { active_only: true } });
