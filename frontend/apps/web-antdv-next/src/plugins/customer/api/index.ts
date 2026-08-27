import type { Recordable } from '@vben/types';

import type { PaginationResult } from '#/types';

import { requestClient } from '#/api/request';

const baseUrl = '/api/v1/erp/customer';

export type MasterStatus = 'ACTIVE' | 'DISABLED';
export type CooperationStatus = 'BLOCKED' | 'NORMAL' | 'SUSPENDED';
export type CustomerType = 'DISTRIBUTOR' | 'END_CUSTOMER' | 'ENTERPRISE' | 'INTERNAL' | 'OTHER';
export type CompanyType = 'COMPANY' | 'INDIVIDUAL' | 'ORGANIZATION';
export type ContactType = 'AFTER_SALES' | 'BUSINESS' | 'FINANCE' | 'OTHER' | 'PURCHASE' | 'QUALITY' | 'RECEIVING' | 'TECHNICAL';
export type AddressType = 'BILLING' | 'DELIVERY' | 'OFFICE' | 'OTHER' | 'REGISTERED' | 'RETURN';

export interface CustomerCategory { id: number; category_code: string; category_name: string; parent_id?: number; status: MasterStatus; sort_no: number; remark?: string; }
export interface CustomerCategoryTreeNode { id: number; code: string; name: string; parent_id?: number; status: MasterStatus; sort_no: number; remark?: string; children: CustomerCategoryTreeNode[]; }
export interface CustomerAddress { id: number; customer_id: number; address_code: string; address_name: string; address_type: AddressType; country: string; province: string; city: string; district: string; detail_address: string; postal_code?: string; contact_name?: string; contact_phone?: string; is_default: boolean; status: MasterStatus; remark?: string; full_address: string; }
export interface CustomerContact { id: number; customer_id: number; contact_name: string; contact_type: ContactType; department?: string; position?: string; phone?: string; mobile?: string; email?: string; wechat?: string; is_primary: boolean; status: MasterStatus; remark?: string; }
export interface Customer { id: number; customer_code: string; customer_name: string; short_name?: string; category_id?: number; category_name?: string; customer_type: CustomerType; company_type?: CompanyType; unified_social_credit_code?: string; tax_number?: string; country?: string; province?: string; city?: string; registered_address?: string; website?: string; status: MasterStatus; cooperation_status: CooperationStatus; sales_enabled: boolean; shipment_enabled: boolean; trace_enabled: boolean; preferred: boolean; default_currency?: string; payment_term?: string; delivery_term?: string; remark?: string; created_time: string; updated_time?: string; contact_count?: number; address_count?: number; default_delivery_address?: { full_address: string; name: string }; }
export type CustomerForm = Omit<Customer, 'id' | 'created_time' | 'updated_time' | 'category_name' | 'contact_count' | 'address_count' | 'default_delivery_address'> & { id?: number };
export type CustomerCategoryForm = Omit<CustomerCategory, 'id'> & { id?: number };
export type CustomerContactForm = Omit<CustomerContact, 'id' | 'customer_id'> & { id?: number };
export type CustomerAddressForm = Omit<CustomerAddress, 'id' | 'customer_id' | 'full_address'> & { id?: number };

export const getCustomerCategoryTreeApi = () => requestClient.get<CustomerCategoryTreeNode[]>(`${baseUrl}/category/tree`);
export const createCustomerCategoryApi = (data: CustomerCategoryForm) => requestClient.post<CustomerCategory>(`${baseUrl}/category`, data);
export const updateCustomerCategoryApi = (id: number, data: CustomerCategoryForm) => requestClient.put<CustomerCategory>(`${baseUrl}/category/${id}`, data);
export const getCustomerListApi = (params?: Recordable<any>) => requestClient.get<PaginationResult<Customer>>(baseUrl, { params });
export const getCustomerApi = (id: number) => requestClient.get<Customer>(`${baseUrl}/${id}`);
export const createCustomerApi = (data: CustomerForm) => requestClient.post<Customer>(baseUrl, data);
export const updateCustomerApi = (id: number, data: CustomerForm) => requestClient.put<Customer>(`${baseUrl}/${id}`, data);
export const updateCustomerStatusApi = (id: number, status: MasterStatus) => requestClient.put<Customer>(`${baseUrl}/${id}/status`, { status });
export const updateCooperationStatusApi = (id: number, cooperation_status: CooperationStatus) => requestClient.put<Customer>(`${baseUrl}/${id}/cooperation-status`, { cooperation_status });
export const getCustomerContactsApi = (id: number) => requestClient.get<CustomerContact[]>(`${baseUrl}/${id}/contacts`);
export const createCustomerContactApi = (id: number, data: CustomerContactForm) => requestClient.post<CustomerContact>(`${baseUrl}/${id}/contacts`, data);
export const updateCustomerContactApi = (id: number, contactId: number, data: CustomerContactForm) => requestClient.put<CustomerContact>(`${baseUrl}/${id}/contacts/${contactId}`, data);
export const updateCustomerContactStatusApi = (id: number, contactId: number, status: MasterStatus) => requestClient.put<CustomerContact>(`${baseUrl}/${id}/contacts/${contactId}/status`, { status });
export const setPrimaryContactApi = (id: number, contactId: number) => requestClient.put<CustomerContact>(`${baseUrl}/${id}/contacts/${contactId}/primary`);
export const getCustomerAddressesApi = (id: number) => requestClient.get<CustomerAddress[]>(`${baseUrl}/${id}/addresses`);
export const createCustomerAddressApi = (id: number, data: CustomerAddressForm) => requestClient.post<CustomerAddress>(`${baseUrl}/${id}/addresses`, data);
export const updateCustomerAddressApi = (id: number, addressId: number, data: CustomerAddressForm) => requestClient.put<CustomerAddress>(`${baseUrl}/${id}/addresses/${addressId}`, data);
export const updateCustomerAddressStatusApi = (id: number, addressId: number, status: MasterStatus) => requestClient.put<CustomerAddress>(`${baseUrl}/${id}/addresses/${addressId}/status`, { status });
export const setDefaultAddressApi = (id: number, addressId: number) => requestClient.put<CustomerAddress>(`${baseUrl}/${id}/addresses/${addressId}/default`);
