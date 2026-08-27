from collections.abc import Sequence

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.customer.enums import AddressStatus, AddressType, ContactStatus, CooperationStatus, CustomerCategoryStatus, CustomerStatus, CustomerType
from backend.plugin.customer.model import Customer, CustomerAddress, CustomerCategory, CustomerContact


class CustomerRepository:
    async def get_category(self, db: AsyncSession, category_id: int) -> CustomerCategory | None:
        return await db.scalar(select(CustomerCategory).where(CustomerCategory.id == category_id, CustomerCategory.deleted == 0))

    async def get_category_by_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> CustomerCategory | None:
        statement = select(CustomerCategory).where(CustomerCategory.category_code == code, CustomerCategory.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(CustomerCategory.id != exclude_id)
        return await db.scalar(statement)

    async def list_categories(self, db: AsyncSession) -> Sequence[CustomerCategory]:
        return (await db.scalars(select(CustomerCategory).where(CustomerCategory.deleted == 0).order_by(CustomerCategory.sort_no, CustomerCategory.id))).all()

    async def create_category(self, db: AsyncSession, data: dict) -> CustomerCategory:
        item = CustomerCategory(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_customer(self, db: AsyncSession, customer_id: int) -> Customer | None:
        return await db.scalar(select(Customer).where(Customer.id == customer_id, Customer.deleted == 0))

    async def get_customer_by_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> Customer | None:
        statement = select(Customer).where(Customer.customer_code == code, Customer.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Customer.id != exclude_id)
        return await db.scalar(statement)

    async def get_customer_by_credit_code(self, db: AsyncSession, code: str, exclude_id: int | None = None) -> Customer | None:
        statement = select(Customer).where(Customer.unified_social_credit_code == code, Customer.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Customer.id != exclude_id)
        return await db.scalar(statement)

    async def create_customer(self, db: AsyncSession, data: dict) -> Customer:
        item = Customer(**data)
        db.add(item)
        await db.flush()
        return item

    async def get_customer_select(self, *, keyword: str | None = None, category_ids: set[int] | None = None,
        customer_type: CustomerType | None = None, country: str | None = None, status: CustomerStatus | None = None,
        cooperation_status: CooperationStatus | None = None, sales_enabled: bool | None = None,
        shipment_enabled: bool | None = None, trace_enabled: bool | None = None, preferred: bool | None = None) -> Select[tuple[Customer]]:
        statement: Select[tuple[Customer]] = select(Customer).where(Customer.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(Customer.customer_code.ilike(like) | Customer.customer_name.ilike(like) | Customer.short_name.ilike(like) | Customer.unified_social_credit_code.ilike(like) | Customer.tax_number.ilike(like))
        if category_ids is not None:
            statement = statement.where(Customer.category_id.in_(category_ids))
        if customer_type is not None: statement = statement.where(Customer.customer_type == customer_type)
        if country: statement = statement.where(Customer.country.ilike(f'%{country.strip()}%'))
        if status is not None: statement = statement.where(Customer.status == status)
        if cooperation_status is not None: statement = statement.where(Customer.cooperation_status == cooperation_status)
        if sales_enabled is not None: statement = statement.where(Customer.sales_enabled == sales_enabled)
        if shipment_enabled is not None: statement = statement.where(Customer.shipment_enabled == shipment_enabled)
        if trace_enabled is not None: statement = statement.where(Customer.trace_enabled == trace_enabled)
        if preferred is not None: statement = statement.where(Customer.preferred == preferred)
        return statement.order_by(Customer.customer_code, Customer.id)

    async def count_contacts(self, db: AsyncSession, customer_id: int) -> int:
        from sqlalchemy import func
        return (await db.scalar(select(func.count()).select_from(CustomerContact).where(CustomerContact.customer_id == customer_id, CustomerContact.deleted == 0))) or 0

    async def count_addresses(self, db: AsyncSession, customer_id: int) -> int:
        from sqlalchemy import func
        return (await db.scalar(select(func.count()).select_from(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.deleted == 0))) or 0

    async def get_contact(self, db: AsyncSession, customer_id: int, contact_id: int) -> CustomerContact | None:
        return await db.scalar(select(CustomerContact).where(CustomerContact.id == contact_id, CustomerContact.customer_id == customer_id, CustomerContact.deleted == 0))

    async def list_contacts(self, db: AsyncSession, customer_id: int) -> Sequence[CustomerContact]:
        return (await db.scalars(select(CustomerContact).where(CustomerContact.customer_id == customer_id, CustomerContact.deleted == 0).order_by(CustomerContact.is_primary.desc(), CustomerContact.id))).all()

    async def create_contact(self, db: AsyncSession, data: dict) -> CustomerContact:
        item = CustomerContact(**data); db.add(item); await db.flush(); return item

    async def clear_primary_contacts(self, db: AsyncSession, customer_id: int, exclude_id: int | None = None) -> None:
        statement = update(CustomerContact).where(CustomerContact.customer_id == customer_id, CustomerContact.deleted == 0).values(is_primary=False)
        if exclude_id is not None: statement = statement.where(CustomerContact.id != exclude_id)
        await db.execute(statement)

    async def get_address(self, db: AsyncSession, customer_id: int, address_id: int) -> CustomerAddress | None:
        return await db.scalar(select(CustomerAddress).where(CustomerAddress.id == address_id, CustomerAddress.customer_id == customer_id, CustomerAddress.deleted == 0))

    async def get_address_by_code(self, db: AsyncSession, customer_id: int, code: str, exclude_id: int | None = None) -> CustomerAddress | None:
        statement = select(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.address_code == code, CustomerAddress.deleted == 0)
        if exclude_id is not None: statement = statement.where(CustomerAddress.id != exclude_id)
        return await db.scalar(statement)

    async def list_addresses(self, db: AsyncSession, customer_id: int, address_type: AddressType | None = None) -> Sequence[CustomerAddress]:
        statement = select(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.deleted == 0)
        if address_type is not None: statement = statement.where(CustomerAddress.address_type == address_type)
        return (await db.scalars(statement.order_by(CustomerAddress.is_default.desc(), CustomerAddress.address_code, CustomerAddress.id))).all()

    async def get_default_delivery_address(self, db: AsyncSession, customer_id: int) -> CustomerAddress | None:
        return await db.scalar(select(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.address_type == AddressType.DELIVERY, CustomerAddress.is_default.is_(True), CustomerAddress.status == AddressStatus.ACTIVE, CustomerAddress.deleted == 0))

    async def create_address(self, db: AsyncSession, data: dict) -> CustomerAddress:
        item = CustomerAddress(**data); db.add(item); await db.flush(); return item

    async def clear_default_delivery_addresses(self, db: AsyncSession, customer_id: int, exclude_id: int | None = None) -> None:
        statement = update(CustomerAddress).where(CustomerAddress.customer_id == customer_id, CustomerAddress.address_type == AddressType.DELIVERY, CustomerAddress.deleted == 0).values(is_default=False)
        if exclude_id is not None: statement = statement.where(CustomerAddress.id != exclude_id)
        await db.execute(statement)


customer_repo = CustomerRepository()
