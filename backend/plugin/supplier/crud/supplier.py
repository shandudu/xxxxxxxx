from collections.abc import Sequence

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.plugin.supplier.enums import (
    ContactStatus,
    CooperationStatus,
    SupplierMaterialStatus,
    SupplierQualityStatus,
    SupplierStatus,
)
from backend.plugin.supplier.model import Supplier, SupplierCategory, SupplierContact, SupplierMaterial, SupplierOperationLog


class SupplierRepository:
    async def get_category(self, db: AsyncSession, category_id: int) -> SupplierCategory | None:
        return await db.scalar(select(SupplierCategory).where(SupplierCategory.id == category_id, SupplierCategory.deleted == 0))

    async def get_category_by_code(
        self, db: AsyncSession, category_code: str, exclude_id: int | None = None
    ) -> SupplierCategory | None:
        statement = select(SupplierCategory).where(
            SupplierCategory.category_code == category_code, SupplierCategory.deleted == 0
        )
        if exclude_id is not None:
            statement = statement.where(SupplierCategory.id != exclude_id)
        return await db.scalar(statement)

    async def list_categories(self, db: AsyncSession) -> Sequence[SupplierCategory]:
        statement = select(SupplierCategory).where(SupplierCategory.deleted == 0).order_by(
            SupplierCategory.sort_no, SupplierCategory.category_code, SupplierCategory.id
        )
        return (await db.scalars(statement)).all()

    async def create_category(self, db: AsyncSession, data: dict) -> SupplierCategory:
        category = SupplierCategory(**data)
        db.add(category)
        await db.flush()
        return category

    async def get_supplier(self, db: AsyncSession, supplier_id: int) -> Supplier | None:
        return await db.scalar(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted == 0))

    async def get_supplier_by_code(self, db: AsyncSession, supplier_code: str, exclude_id: int | None = None) -> Supplier | None:
        statement = select(Supplier).where(Supplier.supplier_code == supplier_code, Supplier.deleted == 0)
        if exclude_id is not None:
            statement = statement.where(Supplier.id != exclude_id)
        return await db.scalar(statement)

    async def get_supplier_by_credit_code(
        self, db: AsyncSession, credit_code: str, exclude_id: int | None = None
    ) -> Supplier | None:
        statement = select(Supplier).where(
            Supplier.unified_social_credit_code == credit_code, Supplier.deleted == 0
        )
        if exclude_id is not None:
            statement = statement.where(Supplier.id != exclude_id)
        return await db.scalar(statement)

    async def create_supplier(self, db: AsyncSession, data: dict) -> Supplier:
        supplier = Supplier(**data)
        db.add(supplier)
        await db.flush()
        return supplier

    async def get_supplier_select(
        self,
        keyword: str | None = None,
        category_id: int | None = None,
        status: SupplierStatus | None = None,
        cooperation_status: CooperationStatus | None = None,
        quality_status: SupplierQualityStatus | None = None,
        preferred: bool | None = None,
    ) -> Select[tuple[Supplier]]:
        statement: Select[tuple[Supplier]] = select(Supplier).where(Supplier.deleted == 0)
        if keyword:
            like = f'%{keyword.strip()}%'
            statement = statement.where(
                Supplier.supplier_code.ilike(like)
                | Supplier.supplier_name.ilike(like)
                | Supplier.short_name.ilike(like)
                | Supplier.unified_social_credit_code.ilike(like)
            )
        if category_id is not None:
            statement = statement.where(Supplier.category_id == category_id)
        if status is not None:
            statement = statement.where(Supplier.status == status)
        if cooperation_status is not None:
            statement = statement.where(Supplier.cooperation_status == cooperation_status)
        if quality_status is not None:
            statement = statement.where(Supplier.quality_status == quality_status)
        if preferred is not None:
            statement = statement.where(Supplier.preferred == preferred)
        return statement.order_by(Supplier.supplier_code, Supplier.id)

    async def get_contact(self, db: AsyncSession, contact_id: int) -> SupplierContact | None:
        return await db.scalar(select(SupplierContact).where(SupplierContact.id == contact_id, SupplierContact.deleted == 0))

    async def list_contacts(self, db: AsyncSession, supplier_id: int) -> Sequence[SupplierContact]:
        statement = select(SupplierContact).where(
            SupplierContact.supplier_id == supplier_id, SupplierContact.deleted == 0
        ).order_by(SupplierContact.is_primary.desc(), SupplierContact.contact_name, SupplierContact.id)
        return (await db.scalars(statement)).all()

    async def clear_primary_contacts(self, db: AsyncSession, supplier_id: int, exclude_id: int | None = None) -> None:
        # Lock the supplier row first so concurrent primary-contact changes serialize even when no primary exists yet.
        await db.execute(select(Supplier.id).where(Supplier.id == supplier_id).with_for_update())
        statement = update(SupplierContact).where(
            SupplierContact.supplier_id == supplier_id,
            SupplierContact.deleted == 0,
            SupplierContact.is_primary.is_(True),
        )
        if exclude_id is not None:
            statement = statement.where(SupplierContact.id != exclude_id)
        await db.execute(statement.values(is_primary=False))

    async def create_contact(self, db: AsyncSession, data: dict) -> SupplierContact:
        contact = SupplierContact(**data)
        db.add(contact)
        await db.flush()
        return contact

    async def get_supplier_material(self, db: AsyncSession, relation_id: int) -> SupplierMaterial | None:
        return await db.scalar(
            select(SupplierMaterial).where(SupplierMaterial.id == relation_id, SupplierMaterial.deleted == 0)
        )

    async def get_supplier_material_by_pair(
        self, db: AsyncSession, supplier_id: int, material_id: int, exclude_id: int | None = None
    ) -> SupplierMaterial | None:
        statement = select(SupplierMaterial).where(
            SupplierMaterial.supplier_id == supplier_id,
            SupplierMaterial.material_id == material_id,
            SupplierMaterial.deleted == 0,
        )
        if exclude_id is not None:
            statement = statement.where(SupplierMaterial.id != exclude_id)
        return await db.scalar(statement)

    async def list_supplier_materials(self, db: AsyncSession, supplier_id: int) -> Sequence[SupplierMaterial]:
        statement = select(SupplierMaterial).where(
            SupplierMaterial.supplier_id == supplier_id, SupplierMaterial.deleted == 0
        ).order_by(SupplierMaterial.preferred.desc(), SupplierMaterial.id)
        return (await db.scalars(statement)).all()

    async def create_supplier_material(self, db: AsyncSession, data: dict) -> SupplierMaterial:
        relation = SupplierMaterial(**data)
        db.add(relation)
        await db.flush()
        return relation

    async def option_suppliers(self, db: AsyncSession, material_id: int | None = None) -> Sequence[Supplier]:
        statement = select(Supplier).where(
            Supplier.deleted == 0,
            Supplier.status == SupplierStatus.ACTIVE,
            Supplier.cooperation_status == CooperationStatus.NORMAL,
            Supplier.purchasing_enabled.is_(True),
        )
        if material_id is not None:
            statement = statement.join(
                SupplierMaterial,
                (SupplierMaterial.supplier_id == Supplier.id) & (SupplierMaterial.deleted == 0),
            ).where(
                SupplierMaterial.material_id == material_id,
                SupplierMaterial.status == SupplierMaterialStatus.ACTIVE,
            )
        return (await db.scalars(statement.order_by(Supplier.preferred.desc(), Supplier.supplier_code).limit(200))).all()

    async def create_operation_log(self, db: AsyncSession, data: dict) -> SupplierOperationLog:
        log = SupplierOperationLog(**data)
        db.add(log)
        await db.flush()
        return log


supplier_repo = SupplierRepository()
