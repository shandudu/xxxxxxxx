from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.customer.enums import AddressStatus, AddressType, ContactStatus, CooperationStatus, CustomerStatus, CustomerType
from backend.plugin.customer.schema.customer import (
    AddressStatusParam, CooperationStatusParam, ContactStatusParam, CreateCustomerAddressParam,
    CreateCustomerCategoryParam, CreateCustomerContactParam, CreateCustomerParam, CustomerAddressDetail,
    CustomerAddressOption, CustomerCategoryDetail, CustomerCategoryTreeNode, CustomerContactDetail,
    CustomerDetail, CustomerListItem, CustomerOption, CustomerStatusParam, UpdateCustomerAddressParam,
    UpdateCustomerCategoryParam, UpdateCustomerContactParam, UpdateCustomerParam,
)
from backend.plugin.customer.service.customer_service import customer_service

router = APIRouter()


@router.get('/category/tree', dependencies=[DependsJwtAuth])
async def get_category_tree(db: CurrentSession) -> ResponseSchemaModel[list[CustomerCategoryTreeNode]]:
    return response_base.success(data=await customer_service.get_category_tree(db))


@router.get('/category', dependencies=[DependsJwtAuth])
async def list_categories(db: CurrentSession) -> ResponseSchemaModel[list[CustomerCategoryDetail]]:
    return response_base.success(data=await customer_service.list_categories(db))


@router.post('/category', dependencies=[Depends(RequestPermission('mes:customer:category')), DependsRBAC])
async def create_category(db: CurrentSessionTransaction, obj: CreateCustomerCategoryParam) -> ResponseSchemaModel[CustomerCategoryDetail]:
    return response_base.success(data=await customer_service.create_category(db, obj))


@router.put('/category/{category_id}', dependencies=[Depends(RequestPermission('mes:customer:category')), DependsRBAC])
async def update_category(db: CurrentSessionTransaction, category_id: Annotated[int, Path(ge=1)], obj: UpdateCustomerCategoryParam) -> ResponseSchemaModel[CustomerCategoryDetail]:
    return response_base.success(data=await customer_service.update_category(db, category_id, obj))


@router.get('/options', dependencies=[DependsJwtAuth])
async def list_options(db: CurrentSession, keyword: Annotated[str | None, Query()] = None, customer_type: Annotated[CustomerType | None, Query()] = None, sales_enabled: Annotated[bool | None, Query()] = None, shipment_enabled: Annotated[bool | None, Query()] = None, trace_enabled: Annotated[bool | None, Query()] = None) -> ResponseSchemaModel[list[CustomerOption]]:
    return response_base.success(data=await customer_service.list_options(db, keyword, customer_type, sales_enabled, shipment_enabled, trace_enabled))


@router.get('', dependencies=[DependsJwtAuth, DependsPagination])
async def list_customers(db: CurrentSession, keyword: Annotated[str | None, Query()] = None, category_id: Annotated[int | None, Query(ge=1)] = None, customer_type: Annotated[CustomerType | None, Query()] = None, country: Annotated[str | None, Query()] = None, status: Annotated[CustomerStatus | None, Query()] = None, cooperation_status: Annotated[CooperationStatus | None, Query()] = None, sales_enabled: Annotated[bool | None, Query()] = None, shipment_enabled: Annotated[bool | None, Query()] = None, trace_enabled: Annotated[bool | None, Query()] = None, preferred: Annotated[bool | None, Query()] = None) -> ResponseSchemaModel[PageData[CustomerListItem]]:
    return response_base.success(data=await customer_service.list_customers(db, keyword, category_id, customer_type, country, status, cooperation_status, sales_enabled, shipment_enabled, trace_enabled, preferred))


@router.get('/{customer_id}', dependencies=[DependsJwtAuth])
async def get_customer(db: CurrentSession, customer_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CustomerDetail]:
    return response_base.success(data=await customer_service.get_customer(db, customer_id))


@router.post('', dependencies=[Depends(RequestPermission('mes:customer:config')), DependsRBAC])
async def create_customer(db: CurrentSessionTransaction, obj: CreateCustomerParam) -> ResponseSchemaModel[CustomerDetail]:
    customer = await customer_service.create_customer(db, obj)
    return response_base.success(data=await customer_service.get_customer(db, customer.id))


@router.put('/{customer_id}', dependencies=[Depends(RequestPermission('mes:customer:config')), DependsRBAC])
async def update_customer(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], obj: UpdateCustomerParam) -> ResponseSchemaModel[CustomerDetail]:
    await customer_service.update_customer(db, customer_id, obj)
    return response_base.success(data=await customer_service.get_customer(db, customer_id))


@router.put('/{customer_id}/status', dependencies=[Depends(RequestPermission('mes:customer:status')), DependsRBAC])
async def update_customer_status(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], obj: CustomerStatusParam) -> ResponseSchemaModel[CustomerDetail]:
    await customer_service.update_status(db, customer_id, obj.status)
    return response_base.success(data=await customer_service.get_customer(db, customer_id))


@router.put('/{customer_id}/cooperation-status', dependencies=[Depends(RequestPermission('mes:customer:status')), DependsRBAC])
async def update_cooperation_status(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], obj: CooperationStatusParam) -> ResponseSchemaModel[CustomerDetail]:
    await customer_service.update_cooperation_status(db, customer_id, obj.cooperation_status)
    return response_base.success(data=await customer_service.get_customer(db, customer_id))


@router.get('/{customer_id}/contacts', dependencies=[DependsJwtAuth])
async def list_contacts(db: CurrentSession, customer_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[CustomerContactDetail]]:
    return response_base.success(data=await customer_service.list_contacts(db, customer_id))


@router.post('/{customer_id}/contacts', dependencies=[Depends(RequestPermission('mes:customer:contact')), DependsRBAC])
async def create_contact(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], obj: CreateCustomerContactParam) -> ResponseSchemaModel[CustomerContactDetail]:
    return response_base.success(data=await customer_service.create_contact(db, customer_id, obj))


@router.put('/{customer_id}/contacts/{contact_id}', dependencies=[Depends(RequestPermission('mes:customer:contact')), DependsRBAC])
async def update_contact(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], contact_id: Annotated[int, Path(ge=1)], obj: UpdateCustomerContactParam) -> ResponseSchemaModel[CustomerContactDetail]:
    return response_base.success(data=await customer_service.update_contact(db, customer_id, contact_id, obj))


@router.put('/{customer_id}/contacts/{contact_id}/status', dependencies=[Depends(RequestPermission('mes:customer:contact')), DependsRBAC])
async def update_contact_status(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], contact_id: Annotated[int, Path(ge=1)], obj: ContactStatusParam) -> ResponseSchemaModel[CustomerContactDetail]:
    return response_base.success(data=await customer_service.update_contact_status(db, customer_id, contact_id, obj.status))


@router.put('/{customer_id}/contacts/{contact_id}/primary', dependencies=[Depends(RequestPermission('mes:customer:contact')), DependsRBAC])
async def set_primary_contact(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], contact_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CustomerContactDetail]:
    return response_base.success(data=await customer_service.set_primary_contact(db, customer_id, contact_id))


@router.get('/{customer_id}/addresses', dependencies=[DependsJwtAuth])
async def list_addresses(db: CurrentSession, customer_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[CustomerAddressDetail]]:
    return response_base.success(data=await customer_service.list_addresses(db, customer_id))


@router.get('/{customer_id}/address-options', dependencies=[DependsJwtAuth])
async def list_address_options(db: CurrentSession, customer_id: Annotated[int, Path(ge=1)], address_type: Annotated[AddressType, Query()] = AddressType.DELIVERY) -> ResponseSchemaModel[list[CustomerAddressOption]]:
    return response_base.success(data=await customer_service.list_address_options(db, customer_id, address_type))


@router.post('/{customer_id}/addresses', dependencies=[Depends(RequestPermission('mes:customer:address')), DependsRBAC])
async def create_address(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], obj: CreateCustomerAddressParam) -> ResponseSchemaModel[CustomerAddressDetail]:
    return response_base.success(data=customer_service._address_item(await customer_service.create_address(db, customer_id, obj)))


@router.put('/{customer_id}/addresses/{address_id}', dependencies=[Depends(RequestPermission('mes:customer:address')), DependsRBAC])
async def update_address(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], address_id: Annotated[int, Path(ge=1)], obj: UpdateCustomerAddressParam) -> ResponseSchemaModel[CustomerAddressDetail]:
    return response_base.success(data=customer_service._address_item(await customer_service.update_address(db, customer_id, address_id, obj)))


@router.put('/{customer_id}/addresses/{address_id}/status', dependencies=[Depends(RequestPermission('mes:customer:address')), DependsRBAC])
async def update_address_status(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], address_id: Annotated[int, Path(ge=1)], obj: AddressStatusParam) -> ResponseSchemaModel[CustomerAddressDetail]:
    return response_base.success(data=customer_service._address_item(await customer_service.update_address_status(db, customer_id, address_id, obj.status)))


@router.put('/{customer_id}/addresses/{address_id}/default', dependencies=[Depends(RequestPermission('mes:customer:address')), DependsRBAC])
async def set_default_address(db: CurrentSessionTransaction, customer_id: Annotated[int, Path(ge=1)], address_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[CustomerAddressDetail]:
    return response_base.success(data=customer_service._address_item(await customer_service.set_default_address(db, customer_id, address_id)))
