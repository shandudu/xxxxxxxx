from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.customer.crud.customer import customer_repo
from backend.plugin.customer.enums import (
    AddressStatus, AddressType, ContactStatus, CooperationStatus, CustomerCategoryStatus, CustomerStatus, CustomerType,
)
from backend.plugin.customer.model import Customer, CustomerAddress, CustomerCategory, CustomerContact
from backend.plugin.customer.schema.customer import (
    CreateCustomerAddressParam, CreateCustomerCategoryParam, CreateCustomerContactParam, CreateCustomerParam,
    CustomerCategoryTreeNode, UpdateCustomerAddressParam, UpdateCustomerCategoryParam, UpdateCustomerContactParam,
    UpdateCustomerParam,
)


class CustomerService:
    @staticmethod
    async def _require_customer(db: AsyncSession, customer_id: int) -> Customer:
        customer = await customer_repo.get_customer(db, customer_id)
        if not customer:
            raise errors.NotFoundError(msg='CUSTOMER_NOT_FOUND')
        return customer

    @staticmethod
    async def _require_category(db: AsyncSession, category_id: int, active_only: bool = True) -> CustomerCategory:
        category = await customer_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='CUSTOMER_CATEGORY_NOT_FOUND')
        if active_only and category.status != CustomerCategoryStatus.ACTIVE:
            raise errors.ConflictError(msg='CUSTOMER_CATEGORY_DISABLED')
        return category

    @staticmethod
    async def _category_descendant_ids(db: AsyncSession, category_id: int) -> set[int]:
        categories = list(await customer_repo.list_categories(db))
        if category_id not in {item.id for item in categories}:
            return set()
        children: dict[int | None, list[int]] = defaultdict(list)
        for category in categories:
            children[category.parent_id].append(category.id)
        result: set[int] = set(); pending = [category_id]
        while pending:
            current = pending.pop()
            if current in result: continue
            result.add(current); pending.extend(children[current])
        return result

    @staticmethod
    async def _category_names(db: AsyncSession, customers: list[Customer]) -> dict[int, str]:
        ids = {item.category_id for item in customers if item.category_id is not None}
        if not ids: return {}
        categories = (await db.scalars(select(CustomerCategory).where(CustomerCategory.id.in_(ids), CustomerCategory.deleted == 0))).all()
        return {item.id: item.category_name for item in categories}

    @staticmethod
    def _full_address(address: CustomerAddress) -> str:
        return ' '.join(part for part in [address.country, address.province, address.city, address.district, address.detail_address] if part)

    @staticmethod
    def _address_item(address: CustomerAddress) -> dict[str, Any]:
        return {
            'id': address.id, 'customer_id': address.customer_id, 'address_code': address.address_code,
            'address_name': address.address_name, 'address_type': address.address_type, 'country': address.country,
            'province': address.province, 'city': address.city, 'district': address.district,
            'detail_address': address.detail_address, 'postal_code': address.postal_code,
            'contact_name': address.contact_name, 'contact_phone': address.contact_phone,
            'is_default': address.is_default, 'status': address.status, 'remark': address.remark,
            'full_address': CustomerService._full_address(address), 'created_time': address.created_time,
            'updated_time': address.updated_time, 'created_by': address.created_by, 'updated_by': address.updated_by,
        }

    @staticmethod
    def _customer_item(customer: Customer, category_names: dict[int, str]) -> dict[str, Any]:
        return {
            'id': customer.id, 'customer_code': customer.customer_code, 'customer_name': customer.customer_name,
            'short_name': customer.short_name, 'category_id': customer.category_id,
            'category_name': category_names.get(customer.category_id) if customer.category_id else None,
            'customer_type': customer.customer_type, 'company_type': customer.company_type,
            'unified_social_credit_code': customer.unified_social_credit_code, 'tax_number': customer.tax_number,
            'country': customer.country, 'province': customer.province, 'city': customer.city,
            'registered_address': customer.registered_address, 'website': customer.website,
            'status': customer.status, 'cooperation_status': customer.cooperation_status,
            'sales_enabled': customer.sales_enabled, 'shipment_enabled': customer.shipment_enabled,
            'trace_enabled': customer.trace_enabled, 'preferred': customer.preferred,
            'default_currency': customer.default_currency, 'payment_term': customer.payment_term,
            'delivery_term': customer.delivery_term, 'remark': customer.remark,
            'created_time': customer.created_time, 'updated_time': customer.updated_time,
        }

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[CustomerCategory]:
        return list(await customer_repo.list_categories(db))

    @staticmethod
    async def get_category_tree(db: AsyncSession) -> list[CustomerCategoryTreeNode]:
        children: dict[int | None, list[CustomerCategory]] = defaultdict(list)
        for category in await CustomerService.list_categories(db): children[category.parent_id].append(category)
        def build(parent_id: int | None, path: set[int] | None = None) -> list[CustomerCategoryTreeNode]:
            nodes = []; current_path = path or set()
            for item in children[parent_id]:
                if item.id in current_path: continue
                nodes.append(CustomerCategoryTreeNode(id=item.id, code=item.category_code, name=item.category_name,
                    parent_id=item.parent_id, status=item.status, sort_no=item.sort_no, remark=item.remark,
                    children=build(item.id, {*current_path, item.id})))
            return nodes
        return build(None)

    @staticmethod
    async def create_category(db: AsyncSession, obj: CreateCustomerCategoryParam) -> CustomerCategory:
        if await customer_repo.get_category_by_code(db, obj.category_code):
            raise errors.ConflictError(msg='CUSTOMER_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None: await CustomerService._require_category(db, obj.parent_id, active_only=False)
        return await customer_repo.create_category(db, obj.model_dump())

    @staticmethod
    async def update_category(db: AsyncSession, category_id: int, obj: UpdateCustomerCategoryParam) -> CustomerCategory:
        category = await CustomerService._require_category(db, category_id, active_only=False)
        if await customer_repo.get_category_by_code(db, obj.category_code, exclude_id=category_id):
            raise errors.ConflictError(msg='CUSTOMER_CATEGORY_CODE_EXISTS')
        candidate = obj.parent_id; seen: set[int] = set()
        while candidate is not None:
            if candidate == category_id or candidate in seen: raise errors.ConflictError(msg='CUSTOMER_CATEGORY_CYCLE')
            seen.add(candidate); parent = await CustomerService._require_category(db, candidate, active_only=False)
            candidate = parent.parent_id
        for key, value in obj.model_dump().items(): setattr(category, key, value)
        return category

    @staticmethod
    async def _validate_customer_unique(db: AsyncSession, obj: CreateCustomerParam | UpdateCustomerParam, exclude_id: int | None = None) -> None:
        if await customer_repo.get_customer_by_code(db, obj.customer_code, exclude_id):
            raise errors.ConflictError(msg='CUSTOMER_CODE_EXISTS')
        if obj.unified_social_credit_code and await customer_repo.get_customer_by_credit_code(db, obj.unified_social_credit_code, exclude_id):
            raise errors.ConflictError(msg='CUSTOMER_CREDIT_CODE_EXISTS')
        if obj.category_id is not None: await CustomerService._require_category(db, obj.category_id)

    @staticmethod
    async def create_customer(db: AsyncSession, obj: CreateCustomerParam) -> Customer:
        await CustomerService._validate_customer_unique(db, obj)
        return await customer_repo.create_customer(db, obj.model_dump())

    @staticmethod
    async def update_customer(db: AsyncSession, customer_id: int, obj: UpdateCustomerParam) -> Customer:
        customer = await CustomerService._require_customer(db, customer_id)
        await CustomerService._validate_customer_unique(db, obj, customer_id)
        for key, value in obj.model_dump().items(): setattr(customer, key, value)
        return customer

    @staticmethod
    async def get_customer(db: AsyncSession, customer_id: int) -> dict[str, Any]:
        customer = await CustomerService._require_customer(db, customer_id)
        data = CustomerService._customer_item(customer, await CustomerService._category_names(db, [customer]))
        default_address = await customer_repo.get_default_delivery_address(db, customer_id)
        data.update(contact_count=await customer_repo.count_contacts(db, customer_id), address_count=await customer_repo.count_addresses(db, customer_id),
            default_delivery_address=(None if not default_address else {'id': default_address.id, 'code': default_address.address_code, 'name': default_address.address_name, 'full_address': CustomerService._full_address(default_address), 'contact_name': default_address.contact_name, 'contact_phone': default_address.contact_phone}),
            created_by=customer.created_by, updated_by=customer.updated_by)
        return data

    @staticmethod
    async def list_customers(db: AsyncSession, keyword: str | None, category_id: int | None, customer_type: CustomerType | None,
        country: str | None, status: CustomerStatus | None, cooperation_status: CooperationStatus | None,
        sales_enabled: bool | None, shipment_enabled: bool | None, trace_enabled: bool | None, preferred: bool | None) -> dict[str, Any]:
        ids = await CustomerService._category_descendant_ids(db, category_id) if category_id else None
        page = await paging_data(db, await customer_repo.get_customer_select(keyword=keyword, category_ids=ids, customer_type=customer_type,
            country=country, status=status, cooperation_status=cooperation_status, sales_enabled=sales_enabled,
            shipment_enabled=shipment_enabled, trace_enabled=trace_enabled, preferred=preferred))
        customers = list(page['items']); names = await CustomerService._category_names(db, customers)
        page['items'] = [CustomerService._customer_item(item, names) for item in customers]
        return page

    @staticmethod
    async def update_status(db: AsyncSession, customer_id: int, status: CustomerStatus) -> Customer:
        customer = await CustomerService._require_customer(db, customer_id); customer.status = status; return customer

    @staticmethod
    async def update_cooperation_status(db: AsyncSession, customer_id: int, status: CooperationStatus) -> Customer:
        customer = await CustomerService._require_customer(db, customer_id); customer.cooperation_status = status; return customer

    @staticmethod
    async def list_options(db: AsyncSession, keyword: str | None, customer_type: CustomerType | None, sales_enabled: bool | None, shipment_enabled: bool | None, trace_enabled: bool | None) -> list[dict[str, Any]]:
        statement = await customer_repo.get_customer_select(keyword=keyword, customer_type=customer_type, status=CustomerStatus.ACTIVE, cooperation_status=CooperationStatus.NORMAL, sales_enabled=sales_enabled, shipment_enabled=shipment_enabled, trace_enabled=trace_enabled)
        return [{'id': item.id, 'code': item.customer_code, 'name': item.customer_name, 'short_name': item.short_name, 'country': item.country, 'preferred': item.preferred} for item in (await db.scalars(statement.limit(100))).all()]

    @staticmethod
    async def list_contacts(db: AsyncSession, customer_id: int) -> list[CustomerContact]:
        await CustomerService._require_customer(db, customer_id); return list(await customer_repo.list_contacts(db, customer_id))

    @staticmethod
    async def create_contact(db: AsyncSession, customer_id: int, obj: CreateCustomerContactParam) -> CustomerContact:
        await CustomerService._require_customer(db, customer_id); data = obj.model_dump(); data['customer_id'] = customer_id
        if data['is_primary'] and data['status'] == ContactStatus.ACTIVE: await customer_repo.clear_primary_contacts(db, customer_id)
        elif data['status'] == ContactStatus.DISABLED: data['is_primary'] = False
        return await customer_repo.create_contact(db, data)

    @staticmethod
    async def update_contact(db: AsyncSession, customer_id: int, contact_id: int, obj: UpdateCustomerContactParam) -> CustomerContact:
        contact = await customer_repo.get_contact(db, customer_id, contact_id)
        if not contact: raise errors.NotFoundError(msg='CUSTOMER_CONTACT_NOT_FOUND')
        data = obj.model_dump()
        if data['is_primary'] and data['status'] == ContactStatus.ACTIVE: await customer_repo.clear_primary_contacts(db, customer_id, contact_id)
        elif data['status'] == ContactStatus.DISABLED: data['is_primary'] = False
        for key, value in data.items(): setattr(contact, key, value)
        return contact

    @staticmethod
    async def update_contact_status(db: AsyncSession, customer_id: int, contact_id: int, status: ContactStatus) -> CustomerContact:
        contact = await customer_repo.get_contact(db, customer_id, contact_id)
        if not contact: raise errors.NotFoundError(msg='CUSTOMER_CONTACT_NOT_FOUND')
        contact.status = status
        if status == ContactStatus.DISABLED: contact.is_primary = False
        return contact

    @staticmethod
    async def set_primary_contact(db: AsyncSession, customer_id: int, contact_id: int) -> CustomerContact:
        contact = await customer_repo.get_contact(db, customer_id, contact_id)
        if not contact: raise errors.NotFoundError(msg='CUSTOMER_CONTACT_NOT_FOUND')
        if contact.status != ContactStatus.ACTIVE: raise errors.ConflictError(msg='CUSTOMER_CONTACT_DISABLED')
        await customer_repo.clear_primary_contacts(db, customer_id, contact_id); contact.is_primary = True; return contact

    @staticmethod
    async def list_addresses(db: AsyncSession, customer_id: int) -> list[dict[str, Any]]:
        await CustomerService._require_customer(db, customer_id); return [CustomerService._address_item(item) for item in await customer_repo.list_addresses(db, customer_id)]

    @staticmethod
    async def _validate_address_default(db: AsyncSession, customer_id: int, address_type: AddressType, status: AddressStatus, is_default: bool, exclude_id: int | None = None) -> bool:
        if not is_default: return False
        if address_type != AddressType.DELIVERY: raise errors.ConflictError(msg='CUSTOMER_ADDRESS_NOT_DELIVERY')
        if status != AddressStatus.ACTIVE: raise errors.ConflictError(msg='CUSTOMER_ADDRESS_DISABLED')
        await customer_repo.clear_default_delivery_addresses(db, customer_id, exclude_id); return True

    @staticmethod
    async def create_address(db: AsyncSession, customer_id: int, obj: CreateCustomerAddressParam) -> CustomerAddress:
        await CustomerService._require_customer(db, customer_id)
        if await customer_repo.get_address_by_code(db, customer_id, obj.address_code): raise errors.ConflictError(msg='CUSTOMER_ADDRESS_CODE_EXISTS')
        data = obj.model_dump(); data['customer_id'] = customer_id
        data['is_default'] = await CustomerService._validate_address_default(db, customer_id, data['address_type'], data['status'], data['is_default'])
        return await customer_repo.create_address(db, data)

    @staticmethod
    async def update_address(db: AsyncSession, customer_id: int, address_id: int, obj: UpdateCustomerAddressParam) -> CustomerAddress:
        address = await customer_repo.get_address(db, customer_id, address_id)
        if not address: raise errors.NotFoundError(msg='CUSTOMER_ADDRESS_NOT_FOUND')
        if await customer_repo.get_address_by_code(db, customer_id, obj.address_code, address_id): raise errors.ConflictError(msg='CUSTOMER_ADDRESS_CODE_EXISTS')
        data = obj.model_dump(); desired_default = data['is_default']
        if address.is_default and (data['address_type'] != AddressType.DELIVERY or data['status'] != AddressStatus.ACTIVE): desired_default = False
        data['is_default'] = await CustomerService._validate_address_default(db, customer_id, data['address_type'], data['status'], desired_default, address_id)
        for key, value in data.items(): setattr(address, key, value)
        return address

    @staticmethod
    async def update_address_status(db: AsyncSession, customer_id: int, address_id: int, status: AddressStatus) -> CustomerAddress:
        address = await customer_repo.get_address(db, customer_id, address_id)
        if not address: raise errors.NotFoundError(msg='CUSTOMER_ADDRESS_NOT_FOUND')
        address.status = status
        if status == AddressStatus.DISABLED: address.is_default = False
        return address

    @staticmethod
    async def set_default_address(db: AsyncSession, customer_id: int, address_id: int) -> CustomerAddress:
        address = await customer_repo.get_address(db, customer_id, address_id)
        if not address: raise errors.NotFoundError(msg='CUSTOMER_ADDRESS_NOT_FOUND')
        await CustomerService._validate_address_default(db, customer_id, address.address_type, address.status, True, address_id)
        address.is_default = True; return address

    @staticmethod
    async def list_address_options(db: AsyncSession, customer_id: int, address_type: AddressType) -> list[dict[str, Any]]:
        await CustomerService._require_customer(db, customer_id)
        return [{'id': item.id, 'code': item.address_code, 'name': item.address_name, 'full_address': CustomerService._full_address(item), 'contact_name': item.contact_name, 'contact_phone': item.contact_phone} for item in await customer_repo.list_addresses(db, customer_id, address_type) if item.status == AddressStatus.ACTIVE]


customer_service = CustomerService()
