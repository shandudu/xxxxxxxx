from collections import defaultdict
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.context import ctx
from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.material.enums import MaterialStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.supplier.crud import supplier_repo
from backend.plugin.supplier.enums import (
    ContactStatus,
    CooperationStatus,
    SupplierCategoryStatus,
    SupplierMaterialStatus,
    SupplierQualityStatus,
    SupplierStatus,
)
from backend.plugin.supplier.model import Supplier, SupplierCategory, SupplierContact, SupplierMaterial
from backend.plugin.supplier.schema.supplier import (
    CreateSupplierCategoryParam,
    CreateSupplierContactParam,
    CreateSupplierMaterialParam,
    CreateSupplierParam,
    SupplierCategoryTreeNode,
    UpdateSupplierCategoryParam,
    UpdateSupplierContactParam,
    UpdateSupplierMaterialParam,
    UpdateSupplierParam,
)


class SupplierService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, LookupError):
            return None

    @staticmethod
    async def _audit(
        db: AsyncSession,
        *,
        object_type: str,
        object_id: int | None,
        object_code: str | None,
        action: str,
        supplier: Supplier | None = None,
        supplier_id: int | None = None,
        supplier_code: str | None = None,
        before_data: Any = None,
        after_data: Any = None,
    ) -> None:
        await supplier_repo.create_operation_log(
            db,
            {
                'supplier_id': supplier.id if supplier else supplier_id,
                'supplier_code': supplier.supplier_code if supplier else supplier_code,
                'object_type': object_type,
                'object_id': object_id,
                'object_code': object_code,
                'action': action,
                'operator_id': SupplierService._operator_id(),
                'before_data': jsonable_encoder(before_data) if before_data is not None else None,
                'after_data': jsonable_encoder(after_data) if after_data is not None else None,
            },
        )

    @staticmethod
    async def _require_category(
        db: AsyncSession, category_id: int, active_only: bool = True
    ) -> SupplierCategory:
        category = await supplier_repo.get_category(db, category_id)
        if not category:
            raise errors.NotFoundError(msg='SUPPLIER_CATEGORY_NOT_FOUND')
        if active_only and category.status != SupplierCategoryStatus.ACTIVE:
            raise errors.ConflictError(msg='SUPPLIER_CATEGORY_DISABLED')
        return category

    @staticmethod
    async def _require_supplier(
        db: AsyncSession, supplier_id: int, active_only: bool = False, usable_only: bool = False
    ) -> Supplier:
        supplier = await supplier_repo.get_supplier(db, supplier_id)
        if not supplier:
            raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
        if (active_only or usable_only) and supplier.status != SupplierStatus.ACTIVE:
            raise errors.ConflictError(msg='SUPPLIER_DISABLED')
        if usable_only and supplier.cooperation_status != CooperationStatus.NORMAL:
            raise errors.ConflictError(msg='SUPPLIER_COOPERATION_NOT_NORMAL')
        return supplier

    @staticmethod
    async def _require_material(db: AsyncSession, material_id: int, active_only: bool = True) -> Material:
        material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
        if not material:
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if active_only and material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='MATERIAL_DISABLED')
        return material

    @staticmethod
    def _category_detail(category: SupplierCategory) -> dict[str, Any]:
        return {
            'id': category.id,
            'category_code': category.category_code,
            'category_name': category.category_name,
            'parent_id': category.parent_id,
            'status': category.status,
            'sort_no': category.sort_no,
            'remark': category.remark,
            'created_time': category.created_time,
            'updated_time': category.updated_time,
        }

    @staticmethod
    def _supplier_detail(supplier: Supplier, category_name: str | None = None) -> dict[str, Any]:
        return {
            'id': supplier.id,
            'supplier_code': supplier.supplier_code,
            'supplier_name': supplier.supplier_name,
            'short_name': supplier.short_name,
            'category_id': supplier.category_id,
            'category_name': category_name,
            'supplier_type': supplier.supplier_type,
            'company_type': supplier.company_type,
            'unified_social_credit_code': supplier.unified_social_credit_code,
            'tax_number': supplier.tax_number,
            'registered_address': supplier.registered_address,
            'business_address': supplier.business_address,
            'website': supplier.website,
            'country': supplier.country,
            'province': supplier.province,
            'city': supplier.city,
            'currency': supplier.currency,
            'payment_terms': supplier.payment_terms,
            'default_lead_time_days': supplier.default_lead_time_days,
            'purchasing_enabled': supplier.purchasing_enabled,
            'quality_enabled': supplier.quality_enabled,
            'trace_enabled': supplier.trace_enabled,
            'preferred': supplier.preferred,
            'status': supplier.status,
            'cooperation_status': supplier.cooperation_status,
            'quality_status': supplier.quality_status,
            'remark': supplier.remark,
            'created_time': supplier.created_time,
            'updated_time': supplier.updated_time,
        }

    @staticmethod
    def _contact_detail(contact: SupplierContact) -> dict[str, Any]:
        return {
            'id': contact.id,
            'supplier_id': contact.supplier_id,
            'contact_name': contact.contact_name,
            'contact_type': contact.contact_type,
            'department': contact.department,
            'position': contact.position,
            'mobile': contact.mobile,
            'telephone': contact.telephone,
            'email': contact.email,
            'wechat': contact.wechat,
            'is_primary': contact.is_primary,
            'status': contact.status,
            'remark': contact.remark,
            'created_time': contact.created_time,
            'updated_time': contact.updated_time,
        }

    @staticmethod
    def _supplier_material_detail(
        relation: SupplierMaterial, material: Material | None = None, unit: str | None = None
    ) -> dict[str, Any]:
        return {
            'id': relation.id,
            'supplier_id': relation.supplier_id,
            'material_id': relation.material_id,
            'material_code': material.material_code if material else None,
            'material_name': material.material_name if material else None,
            'material_specification': material.specification if material else None,
            'unit': unit,
            'supplier_material_code': relation.supplier_material_code,
            'supplier_material_name': relation.supplier_material_name,
            'status': relation.status,
            'preferred': relation.preferred,
            'minimum_order_quantity': relation.minimum_order_quantity,
            'lead_time_days': relation.lead_time_days,
            'quality_inspection_required': relation.quality_inspection_required,
            'remark': relation.remark,
            'created_time': relation.created_time,
            'updated_time': relation.updated_time,
        }

    async def list_categories(self, db: AsyncSession) -> list[dict[str, Any]]:
        return [self._category_detail(item) for item in await supplier_repo.list_categories(db)]

    async def get_category_tree(self, db: AsyncSession) -> list[SupplierCategoryTreeNode]:
        categories = await supplier_repo.list_categories(db)
        children: dict[int | None, list[SupplierCategory]] = defaultdict(list)
        for category in categories:
            children[category.parent_id].append(category)

        def build(parent_id: int | None, path: set[int] | None = None) -> list[SupplierCategoryTreeNode]:
            current_path = path or set()
            result: list[SupplierCategoryTreeNode] = []
            for category in children[parent_id]:
                if category.id in current_path:
                    continue
                result.append(
                    SupplierCategoryTreeNode(
                        id=category.id,
                        code=category.category_code,
                        name=category.category_name,
                        parent_id=category.parent_id,
                        status=category.status,
                        sort_no=category.sort_no,
                        children=build(category.id, {*current_path, category.id}),
                    )
                )
            return result

        return build(None)

    async def create_category(self, db: AsyncSession, obj: CreateSupplierCategoryParam) -> dict[str, Any]:
        if await supplier_repo.get_category_by_code(db, obj.category_code):
            raise errors.ConflictError(msg='SUPPLIER_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            await self._require_category(db, obj.parent_id)
        category = await supplier_repo.create_category(db, obj.model_dump())
        detail = self._category_detail(category)
        await self._audit(
            db, object_type='SUPPLIER_CATEGORY', object_id=category.id, object_code=category.category_code,
            action='CREATE', after_data=detail
        )
        return detail

    async def update_category(
        self, db: AsyncSession, category_id: int, obj: UpdateSupplierCategoryParam
    ) -> dict[str, Any]:
        category = await self._require_category(db, category_id, active_only=False)
        before = self._category_detail(category)
        if await supplier_repo.get_category_by_code(db, obj.category_code, exclude_id=category_id):
            raise errors.ConflictError(msg='SUPPLIER_CATEGORY_CODE_EXISTS')
        if obj.parent_id is not None:
            if obj.parent_id == category_id:
                raise errors.ConflictError(msg='SUPPLIER_CATEGORY_CYCLE')
            candidate_id: int | None = obj.parent_id
            seen: set[int] = set()
            while candidate_id is not None:
                if candidate_id in seen or candidate_id == category_id:
                    raise errors.ConflictError(msg='SUPPLIER_CATEGORY_CYCLE')
                seen.add(candidate_id)
                candidate = await self._require_category(db, candidate_id)
                candidate_id = candidate.parent_id
        for key, value in obj.model_dump().items():
            setattr(category, key, value)
        await db.flush()
        detail = self._category_detail(category)
        await self._audit(
            db, object_type='SUPPLIER_CATEGORY', object_id=category.id, object_code=category.category_code,
            action='UPDATE', before_data=before, after_data=detail
        )
        return detail

    async def update_category_status(
        self, db: AsyncSession, category_id: int, status: SupplierCategoryStatus
    ) -> dict[str, Any]:
        category = await self._require_category(db, category_id, active_only=False)
        before = self._category_detail(category)
        category.status = status
        await db.flush()
        detail = self._category_detail(category)
        await self._audit(
            db, object_type='SUPPLIER_CATEGORY', object_id=category.id, object_code=category.category_code,
            action='STATUS', before_data=before, after_data=detail
        )
        return detail

    async def create_supplier(self, db: AsyncSession, obj: CreateSupplierParam) -> dict[str, Any]:
        if await supplier_repo.get_supplier_by_code(db, obj.supplier_code):
            raise errors.ConflictError(msg='SUPPLIER_CODE_EXISTS')
        if obj.unified_social_credit_code and await supplier_repo.get_supplier_by_credit_code(
            db, obj.unified_social_credit_code
        ):
            raise errors.ConflictError(msg='SUPPLIER_CREDIT_CODE_EXISTS')
        category = await self._require_category(db, obj.category_id)
        supplier = await supplier_repo.create_supplier(db, obj.model_dump())
        supplier.created_by = self._operator_id()
        detail = self._supplier_detail(supplier, category.category_name)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER', object_id=supplier.id, object_code=supplier.supplier_code,
            action='CREATE', after_data=detail
        )
        return detail

    async def get_supplier(self, db: AsyncSession, supplier_id: int) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id)
        category = await self._require_category(db, supplier.category_id, active_only=False)
        return self._supplier_detail(supplier, category.category_name)

    async def list_suppliers(
        self,
        db: AsyncSession,
        keyword: str | None,
        category_id: int | None,
        status: SupplierStatus | None,
        cooperation_status: CooperationStatus | None,
        quality_status: SupplierQualityStatus | None,
        preferred: bool | None,
    ) -> dict[str, Any]:
        statement = await supplier_repo.get_supplier_select(
            keyword, category_id, status, cooperation_status, quality_status, preferred
        )
        page_data = await paging_data(db, statement)
        suppliers = list(page_data['items'])
        category_ids = {item.category_id for item in suppliers}
        categories = (await db.scalars(select(SupplierCategory).where(SupplierCategory.id.in_(category_ids)))).all() if category_ids else []
        category_names = {item.id: item.category_name for item in categories}
        page_data['items'] = [self._supplier_detail(item, category_names.get(item.category_id)) for item in suppliers]
        return page_data

    async def update_supplier(self, db: AsyncSession, supplier_id: int, obj: UpdateSupplierParam) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id)
        before = self._supplier_detail(supplier)
        if await supplier_repo.get_supplier_by_code(db, obj.supplier_code, exclude_id=supplier_id):
            raise errors.ConflictError(msg='SUPPLIER_CODE_EXISTS')
        if obj.unified_social_credit_code and await supplier_repo.get_supplier_by_credit_code(
            db, obj.unified_social_credit_code, exclude_id=supplier_id
        ):
            raise errors.ConflictError(msg='SUPPLIER_CREDIT_CODE_EXISTS')
        category = await self._require_category(db, obj.category_id, active_only=obj.category_id != supplier.category_id)
        for key, value in obj.model_dump().items():
            setattr(supplier, key, value)
        supplier.updated_by = self._operator_id()
        await db.flush()
        detail = self._supplier_detail(supplier, category.category_name)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER', object_id=supplier.id, object_code=supplier.supplier_code,
            action='UPDATE', before_data=before, after_data=detail
        )
        return detail

    async def update_supplier_status(
        self, db: AsyncSession, supplier_id: int, status: SupplierStatus
    ) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id)
        before = self._supplier_detail(supplier)
        supplier.status = status
        supplier.updated_by = self._operator_id()
        await db.flush()
        detail = await self.get_supplier(db, supplier_id)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER', object_id=supplier.id, object_code=supplier.supplier_code,
            action='STATUS', before_data=before, after_data=detail
        )
        return detail

    async def update_supplier_cooperation(
        self, db: AsyncSession, supplier_id: int, cooperation_status: CooperationStatus
    ) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id)
        before = self._supplier_detail(supplier)
        supplier.cooperation_status = cooperation_status
        supplier.updated_by = self._operator_id()
        await db.flush()
        detail = await self.get_supplier(db, supplier_id)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER', object_id=supplier.id, object_code=supplier.supplier_code,
            action='COOPERATION', before_data=before, after_data=detail
        )
        return detail

    async def update_supplier_quality(
        self, db: AsyncSession, supplier_id: int, quality_status: SupplierQualityStatus
    ) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id)
        before = self._supplier_detail(supplier)
        supplier.quality_status = quality_status
        supplier.updated_by = self._operator_id()
        await db.flush()
        detail = await self.get_supplier(db, supplier_id)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER', object_id=supplier.id, object_code=supplier.supplier_code,
            action='QUALITY', before_data=before, after_data=detail
        )
        return detail

    async def supplier_options(self, db: AsyncSession, material_id: int | None = None) -> list[dict[str, Any]]:
        if material_id is not None:
            await self._require_material(db, material_id)
        suppliers = await supplier_repo.option_suppliers(db, material_id)
        return [
            {
                'id': item.id,
                'code': item.supplier_code,
                'name': item.supplier_name,
                'short_name': item.short_name,
                'category_id': item.category_id,
                'preferred': item.preferred,
            }
            for item in suppliers
        ]

    async def list_contacts(self, db: AsyncSession, supplier_id: int) -> list[dict[str, Any]]:
        await self._require_supplier(db, supplier_id)
        return [self._contact_detail(item) for item in await supplier_repo.list_contacts(db, supplier_id)]

    async def create_contact(
        self, db: AsyncSession, supplier_id: int, obj: CreateSupplierContactParam
    ) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id, active_only=True)
        if obj.is_primary:
            await supplier_repo.clear_primary_contacts(db, supplier_id)
        contact = await supplier_repo.create_contact(db, {'supplier_id': supplier_id, **obj.model_dump()})
        detail = self._contact_detail(contact)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_CONTACT', object_id=contact.id, object_code=contact.contact_name,
            action='CREATE', after_data=detail
        )
        return detail

    async def update_contact(
        self, db: AsyncSession, contact_id: int, obj: UpdateSupplierContactParam
    ) -> dict[str, Any]:
        contact = await supplier_repo.get_contact(db, contact_id)
        if not contact:
            raise errors.NotFoundError(msg='SUPPLIER_CONTACT_NOT_FOUND')
        supplier = await self._require_supplier(db, contact.supplier_id)
        before = self._contact_detail(contact)
        if obj.is_primary:
            await supplier_repo.clear_primary_contacts(db, contact.supplier_id, exclude_id=contact.id)
        for key, value in obj.model_dump().items():
            setattr(contact, key, value)
        await db.flush()
        detail = self._contact_detail(contact)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_CONTACT', object_id=contact.id, object_code=contact.contact_name,
            action='UPDATE', before_data=before, after_data=detail
        )
        return detail

    async def set_contact_primary(self, db: AsyncSession, contact_id: int) -> dict[str, Any]:
        contact = await supplier_repo.get_contact(db, contact_id)
        if not contact:
            raise errors.NotFoundError(msg='SUPPLIER_CONTACT_NOT_FOUND')
        supplier = await self._require_supplier(db, contact.supplier_id, active_only=True)
        if contact.status != ContactStatus.ACTIVE:
            raise errors.ConflictError(msg='SUPPLIER_CONTACT_DISABLED')
        before = self._contact_detail(contact)
        await supplier_repo.clear_primary_contacts(db, contact.supplier_id, exclude_id=contact.id)
        contact.is_primary = True
        await db.flush()
        detail = self._contact_detail(contact)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_CONTACT', object_id=contact.id, object_code=contact.contact_name,
            action='SET_PRIMARY', before_data=before, after_data=detail
        )
        return detail

    async def update_contact_status(
        self, db: AsyncSession, contact_id: int, status: ContactStatus
    ) -> dict[str, Any]:
        contact = await supplier_repo.get_contact(db, contact_id)
        if not contact:
            raise errors.NotFoundError(msg='SUPPLIER_CONTACT_NOT_FOUND')
        supplier = await self._require_supplier(db, contact.supplier_id)
        before = self._contact_detail(contact)
        contact.status = status
        if status == ContactStatus.DISABLED:
            contact.is_primary = False
        await db.flush()
        detail = self._contact_detail(contact)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_CONTACT', object_id=contact.id, object_code=contact.contact_name,
            action='STATUS', before_data=before, after_data=detail
        )
        return detail

    async def _supplier_material_details(
        self, db: AsyncSession, relations: list[SupplierMaterial]
    ) -> list[dict[str, Any]]:
        material_ids = {item.material_id for item in relations}
        materials = (await db.scalars(select(Material).where(Material.id.in_(material_ids)))).all() if material_ids else []
        material_map = {item.id: item for item in materials}
        unit_ids = {item.base_unit_id for item in materials}
        units = (await db.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids)))).all() if unit_ids else []
        unit_map = {item.id: item.unit_code for item in units}
        return [
            self._supplier_material_detail(item, material_map.get(item.material_id), unit_map.get(material_map[item.material_id].base_unit_id) if item.material_id in material_map else None)
            for item in relations
        ]

    async def list_supplier_materials(self, db: AsyncSession, supplier_id: int) -> list[dict[str, Any]]:
        await self._require_supplier(db, supplier_id)
        return await self._supplier_material_details(db, list(await supplier_repo.list_supplier_materials(db, supplier_id)))

    async def create_supplier_material(
        self, db: AsyncSession, supplier_id: int, obj: CreateSupplierMaterialParam
    ) -> dict[str, Any]:
        supplier = await self._require_supplier(db, supplier_id, usable_only=True)
        if not supplier.purchasing_enabled:
            raise errors.ConflictError(msg='SUPPLIER_PURCHASING_DISABLED')
        material = await self._require_material(db, obj.material_id)
        if await supplier_repo.get_supplier_material_by_pair(db, supplier_id, obj.material_id):
            raise errors.ConflictError(msg='SUPPLIER_MATERIAL_EXISTS')
        relation = await supplier_repo.create_supplier_material(db, {'supplier_id': supplier_id, **obj.model_dump()})
        detail = self._supplier_material_detail(relation, material)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_MATERIAL', object_id=relation.id,
            object_code=material.material_code, action='CREATE', after_data=detail
        )
        return detail

    async def update_supplier_material(
        self, db: AsyncSession, relation_id: int, obj: UpdateSupplierMaterialParam
    ) -> dict[str, Any]:
        relation = await supplier_repo.get_supplier_material(db, relation_id)
        if not relation:
            raise errors.NotFoundError(msg='SUPPLIER_MATERIAL_NOT_FOUND')
        supplier = await self._require_supplier(db, relation.supplier_id)
        before = (await self._supplier_material_details(db, [relation]))[0]
        material = await self._require_material(db, obj.material_id, active_only=obj.material_id != relation.material_id)
        if await supplier_repo.get_supplier_material_by_pair(
            db, relation.supplier_id, obj.material_id, exclude_id=relation_id
        ):
            raise errors.ConflictError(msg='SUPPLIER_MATERIAL_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(relation, key, value)
        await db.flush()
        detail = self._supplier_material_detail(relation, material)
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_MATERIAL', object_id=relation.id,
            object_code=material.material_code, action='UPDATE', before_data=before, after_data=detail
        )
        return detail

    async def update_supplier_material_status(
        self, db: AsyncSession, relation_id: int, status: SupplierMaterialStatus
    ) -> dict[str, Any]:
        relation = await supplier_repo.get_supplier_material(db, relation_id)
        if not relation:
            raise errors.NotFoundError(msg='SUPPLIER_MATERIAL_NOT_FOUND')
        supplier = await self._require_supplier(db, relation.supplier_id)
        before = (await self._supplier_material_details(db, [relation]))[0]
        relation.status = status
        await db.flush()
        detail = (await self._supplier_material_details(db, [relation]))[0]
        await self._audit(
            db, supplier=supplier, object_type='SUPPLIER_MATERIAL', object_id=relation.id,
            object_code=detail.get('material_code'), action='STATUS', before_data=before, after_data=detail
        )
        return detail


supplier_service = SupplierService()
