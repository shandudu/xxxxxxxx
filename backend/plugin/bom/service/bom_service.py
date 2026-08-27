from collections import defaultdict, deque
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.bom.crud.bom import bom_repo
from backend.plugin.bom.enums import BomStatus
from backend.plugin.bom.model import Bom, BomItem
from backend.plugin.bom.schema.bom import (
    BomCompareChange,
    BomCompareResult,
    BomDetail,
    BomItemDetail,
    BomListItem,
    BomOption,
    BomTree,
    BomTreeNode,
    BomValidationResult,
    CalculateBomParam,
    CopyBomParam,
    CreateBomItemParam,
    CreateBomParam,
    MaterialRequirement,
    MaterialSummary,
    UpdateBomItemParam,
    UpdateBomParam,
)
from backend.plugin.material.crud.material import material_repo
from backend.plugin.material.enums import CategoryStatus, MaterialStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.utils.timezone import timezone


class BomService:
    max_tree_depth = 20

    @staticmethod
    async def _require_bom(db: AsyncSession, bom_id: int) -> Bom:
        bom = await bom_repo.get(db, bom_id)
        if not bom:
            raise errors.NotFoundError(msg='BOM_NOT_FOUND')
        return bom

    @staticmethod
    async def _require_product(db: AsyncSession, material_id: int) -> Material:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='BOM_PRODUCT_NOT_FOUND')
        if material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='BOM_PRODUCT_DISABLED')
        if not material.producible:
            raise errors.ConflictError(msg='BOM_PRODUCT_NOT_PRODUCIBLE')
        return material

    @staticmethod
    async def _require_component(db: AsyncSession, material_id: int) -> Material:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='BOM_COMPONENT_NOT_FOUND')
        if material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='BOM_COMPONENT_DISABLED')
        return material

    @staticmethod
    async def _require_unit(db: AsyncSession, unit_id: int) -> UnitOfMeasure:
        unit = await material_repo.get_unit(db, unit_id)
        if not unit:
            raise errors.NotFoundError(msg='BOM_UNIT_NOT_FOUND')
        if unit.status != CategoryStatus.ACTIVE:
            raise errors.ConflictError(msg='BOM_UNIT_DISABLED')
        return unit

    @staticmethod
    async def _material_map(db: AsyncSession, material_ids: set[int]) -> dict[int, Material]:
        if not material_ids:
            return {}
        materials = (
            await db.scalars(select(Material).where(Material.id.in_(material_ids), Material.deleted == 0))
        ).all()
        return {material.id: material for material in materials}

    @staticmethod
    async def _unit_map(db: AsyncSession, unit_ids: set[int]) -> dict[int, UnitOfMeasure]:
        if not unit_ids:
            return {}
        units = (await db.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids)))).all()
        return {unit.id: unit for unit in units}

    @staticmethod
    def _summary(material: Material, unit: UnitOfMeasure | None) -> MaterialSummary:
        return MaterialSummary(
            id=material.id,
            code=material.material_code,
            name=material.material_name,
            specification=material.specification,
            model=material.model,
            unit=unit.unit_code if unit else '',
        )

    @staticmethod
    async def _item_detail(
        db: AsyncSession,
        item: BomItem,
        material_map: dict[int, Material] | None = None,
        unit_map: dict[int, UnitOfMeasure] | None = None,
    ) -> BomItemDetail:
        material_map = material_map or await BomService._material_map(db, {item.component_material_id})
        unit_map = unit_map or await BomService._unit_map(db, {item.unit_id})
        component = material_map.get(item.component_material_id)
        if not component:
            raise errors.NotFoundError(msg='BOM_COMPONENT_NOT_FOUND')
        return BomItemDetail(
            id=item.id,
            bom_id=item.bom_id,
            line_no=item.line_no,
            component_material_id=item.component_material_id,
            quantity=item.quantity,
            unit_id=item.unit_id,
            loss_rate=item.loss_rate,
            fixed_loss_qty=item.fixed_loss_qty,
            is_optional=item.is_optional,
            remark=item.remark,
            sort_no=item.sort_no,
            component=BomService._summary(component, unit_map.get(item.unit_id)),
            created_time=item.created_time,
            updated_time=item.updated_time,
        )

    @staticmethod
    async def _list_item_details(db: AsyncSession, items: list[BomItem]) -> list[BomItemDetail]:
        material_map = await BomService._material_map(db, {item.component_material_id for item in items})
        unit_map = await BomService._unit_map(db, {item.unit_id for item in items})
        return [await BomService._item_detail(db, item, material_map, unit_map) for item in items]

    @staticmethod
    async def _to_list_item(db: AsyncSession, bom: Bom, with_items: bool = False) -> BomListItem | BomDetail:
        product_map = await BomService._material_map(db, {bom.product_material_id})
        product = product_map.get(bom.product_material_id)
        if not product:
            raise errors.NotFoundError(msg='BOM_PRODUCT_NOT_FOUND')
        unit_map = await BomService._unit_map(db, {product.base_unit_id})
        base = dict(
            id=bom.id,
            bom_code=bom.bom_code,
            bom_version=bom.bom_version,
            product_material_id=bom.product_material_id,
            status=bom.status,
            base_quantity=bom.base_quantity,
            effective_from=bom.effective_from,
            effective_to=bom.effective_to,
            is_default=bom.is_default,
            remark=bom.remark,
            product=BomService._summary(product, unit_map.get(product.base_unit_id)),
            created_time=bom.created_time,
            updated_time=bom.updated_time,
        )
        if not with_items:
            return BomListItem(**base)
        items = list(await bom_repo.get_items(db, bom.id))
        return BomDetail(items=await BomService._list_item_details(db, items), **base)

    @staticmethod
    async def _ensure_draft(bom: Bom) -> None:
        if bom.status != BomStatus.DRAFT:
            raise errors.ConflictError(msg='BOM_NOT_DRAFT')

    @staticmethod
    async def _ensure_active(bom: Bom) -> None:
        if bom.status != BomStatus.ACTIVE:
            raise errors.ConflictError(msg='BOM_NOT_ACTIVE')

    @staticmethod
    async def create_bom(db: AsyncSession, obj: CreateBomParam) -> Bom:
        if await bom_repo.get_by_code(db, obj.bom_code):
            raise errors.ConflictError(msg='BOM_CODE_EXISTS')
        if await bom_repo.get_by_product_version(db, obj.product_material_id, obj.bom_version):
            raise errors.ConflictError(msg='BOM_VERSION_EXISTS')
        await BomService._require_product(db, obj.product_material_id)
        return await bom_repo.create(db, {**obj.model_dump(), 'status': BomStatus.DRAFT, 'is_default': False})

    @staticmethod
    async def update_bom(db: AsyncSession, bom_id: int, obj: UpdateBomParam) -> Bom:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_draft(bom)
        if await bom_repo.get_by_code(db, obj.bom_code, exclude_id=bom_id):
            raise errors.ConflictError(msg='BOM_CODE_EXISTS')
        if await bom_repo.get_by_product_version(db, obj.product_material_id, obj.bom_version, exclude_id=bom_id):
            raise errors.ConflictError(msg='BOM_VERSION_EXISTS')
        await BomService._require_product(db, obj.product_material_id)
        await bom_repo.update(bom, obj.model_dump())
        return bom

    @staticmethod
    async def get_bom(db: AsyncSession, bom_id: int) -> BomDetail:
        return await BomService._to_list_item(db, await BomService._require_bom(db, bom_id), with_items=True)  # type: ignore[return-value]

    @staticmethod
    async def list_boms(
        db: AsyncSession,
        keyword: str | None,
        product_keyword: str | None,
        product_material_id: int | None,
        status: BomStatus | None,
        is_default: bool | None,
        effective_date: datetime | None,
    ) -> dict[str, Any]:
        statement = await bom_repo.get_select(
            keyword=keyword,
            product_keyword=product_keyword,
            product_material_id=product_material_id,
            status=status,
            is_default=is_default,
            effective_date=effective_date,
        )
        page_data = await paging_data(db, statement)
        page_data['items'] = [await BomService._to_list_item(db, bom) for bom in page_data['items']]
        return page_data

    @staticmethod
    async def _validate_item_reference(
        db: AsyncSession,
        product_material_id: int,
        obj: CreateBomItemParam | UpdateBomItemParam,
    ) -> dict[str, Any]:
        if obj.component_material_id == product_material_id:
            raise errors.ConflictError(msg='BOM_SELF_REFERENCE')
        component = await BomService._require_component(db, obj.component_material_id)
        unit_id = obj.unit_id or component.base_unit_id
        if unit_id != component.base_unit_id:
            raise errors.ConflictError(msg='BOM_UNIT_MISMATCH')
        await BomService._require_unit(db, unit_id)
        return {**obj.model_dump(), 'unit_id': unit_id}

    @staticmethod
    async def check_bom_cycle(
        db: AsyncSession, product_material_id: int, component_material_id: int
    ) -> bool:
        if product_material_id == component_material_id:
            return True
        boms = list(await bom_repo.get_all(db, {BomStatus.DRAFT, BomStatus.ACTIVE}))
        if not boms:
            return False
        bom_ids = {bom.id for bom in boms}
        items = [item for item in await bom_repo.get_all_items(db) if item.bom_id in bom_ids]
        graph: dict[int, set[int]] = defaultdict(set)
        for bom in boms:
            for item in items:
                if item.bom_id == bom.id:
                    graph[bom.product_material_id].add(item.component_material_id)

        pending = deque([component_material_id])
        visited: set[int] = set()
        while pending:
            current = pending.popleft()
            if current == product_material_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(graph.get(current, set()) - visited)
        return False

    @staticmethod
    async def _validate_bom(db: AsyncSession, bom: Bom) -> list[str]:
        validation_errors: list[str] = []
        product = await material_repo.get_material(db, bom.product_material_id)
        if not product:
            validation_errors.append('BOM_PRODUCT_NOT_FOUND')
        else:
            if product.status != MaterialStatus.ACTIVE:
                validation_errors.append('BOM_PRODUCT_DISABLED')
            if not product.producible:
                validation_errors.append('BOM_PRODUCT_NOT_PRODUCIBLE')
        if bom.effective_from and bom.effective_to and bom.effective_from > bom.effective_to:
            validation_errors.append('BOM_INVALID_EFFECTIVE_DATE')

        items = list(await bom_repo.get_items(db, bom.id))
        if not items:
            validation_errors.append('BOM_ITEMS_EMPTY')
        component_ids: set[int] = set()
        for item in items:
            if item.component_material_id in component_ids:
                validation_errors.append('BOM_COMPONENT_DUPLICATED')
            component_ids.add(item.component_material_id)
            component = await material_repo.get_material(db, item.component_material_id)
            if not component:
                validation_errors.append('BOM_COMPONENT_NOT_FOUND')
                continue
            if component.status != MaterialStatus.ACTIVE:
                validation_errors.append('BOM_COMPONENT_DISABLED')
            if component.id == bom.product_material_id:
                validation_errors.append('BOM_SELF_REFERENCE')
            if item.unit_id != component.base_unit_id:
                validation_errors.append('BOM_UNIT_MISMATCH')
            if item.quantity <= 0 or item.loss_rate < 0 or item.fixed_loss_qty < 0:
                validation_errors.append('BOM_COMPONENT_QUANTITY_INVALID')
            if await BomService.check_bom_cycle(db, bom.product_material_id, component.id):
                validation_errors.append('BOM_CYCLE_DETECTED')
        return list(dict.fromkeys(validation_errors))

    @staticmethod
    async def validate_bom(db: AsyncSession, bom_id: int) -> BomValidationResult:
        bom = await BomService._require_bom(db, bom_id)
        validation_errors = await BomService._validate_bom(db, bom)
        return BomValidationResult(valid=not validation_errors, errors=validation_errors)

    @staticmethod
    async def add_item(db: AsyncSession, bom_id: int, obj: CreateBomItemParam) -> BomItem:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_draft(bom)
        if await bom_repo.get_item_by_line_no(db, bom_id, obj.line_no):
            raise errors.ConflictError(msg='BOM_LINE_NO_EXISTS')
        existing_items = await bom_repo.get_items(db, bom_id)
        if any(item.component_material_id == obj.component_material_id for item in existing_items):
            raise errors.ConflictError(msg='BOM_COMPONENT_DUPLICATED')
        data = await BomService._validate_item_reference(db, bom.product_material_id, obj)
        if await BomService.check_bom_cycle(db, bom.product_material_id, obj.component_material_id):
            raise errors.ConflictError(msg='BOM_CYCLE_DETECTED')
        return await bom_repo.create_item(db, {'bom_id': bom_id, **data})

    @staticmethod
    async def update_item(db: AsyncSession, bom_id: int, item_id: int, obj: UpdateBomItemParam) -> BomItem:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_draft(bom)
        item = await bom_repo.get_item(db, bom_id, item_id)
        if not item:
            raise errors.NotFoundError(msg='BOM_ITEM_NOT_FOUND')
        if await bom_repo.get_item_by_line_no(db, bom_id, obj.line_no, exclude_id=item_id):
            raise errors.ConflictError(msg='BOM_LINE_NO_EXISTS')
        existing_items = await bom_repo.get_items(db, bom_id)
        if any(
            other.id != item_id and other.component_material_id == obj.component_material_id for other in existing_items
        ):
            raise errors.ConflictError(msg='BOM_COMPONENT_DUPLICATED')
        data = await BomService._validate_item_reference(db, bom.product_material_id, obj)
        if await BomService.check_bom_cycle(db, bom.product_material_id, obj.component_material_id):
            raise errors.ConflictError(msg='BOM_CYCLE_DETECTED')
        for key, value in data.items():
            setattr(item, key, value)
        return item

    @staticmethod
    async def delete_item(db: AsyncSession, bom_id: int, item_id: int) -> None:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_draft(bom)
        item = await bom_repo.get_item(db, bom_id, item_id)
        if not item:
            raise errors.NotFoundError(msg='BOM_ITEM_NOT_FOUND')
        item.deleted = item.id
        item.deleted_time = timezone.now()

    @staticmethod
    async def copy_bom(db: AsyncSession, bom_id: int, obj: CopyBomParam) -> BomDetail:
        source = await BomService._require_bom(db, bom_id)
        if await bom_repo.get_by_code(db, obj.new_bom_code):
            raise errors.ConflictError(msg='BOM_CODE_EXISTS')
        if await bom_repo.get_by_product_version(db, source.product_material_id, obj.new_version):
            raise errors.ConflictError(msg='BOM_VERSION_EXISTS')
        copied = await bom_repo.create(
            db,
            {
                'bom_code': obj.new_bom_code,
                'product_material_id': source.product_material_id,
                'bom_version': obj.new_version,
                'base_quantity': source.base_quantity,
                'status': BomStatus.DRAFT,
                'effective_from': obj.effective_from if obj.effective_from is not None else source.effective_from,
                'effective_to': obj.effective_to if obj.effective_to is not None else source.effective_to,
                'is_default': False,
                'remark': obj.remark if obj.remark is not None else source.remark,
            },
        )
        for source_item in await bom_repo.get_items(db, source.id):
            await bom_repo.create_item(
                db,
                {
                    'bom_id': copied.id,
                    'line_no': source_item.line_no,
                    'component_material_id': source_item.component_material_id,
                    'quantity': source_item.quantity,
                    'unit_id': source_item.unit_id,
                    'loss_rate': source_item.loss_rate,
                    'fixed_loss_qty': source_item.fixed_loss_qty,
                    'is_optional': source_item.is_optional,
                    'remark': source_item.remark,
                    'sort_no': source_item.sort_no,
                },
            )
        return await BomService.get_bom(db, copied.id)

    @staticmethod
    async def activate_bom(db: AsyncSession, bom_id: int) -> Bom:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_draft(bom)
        validation = await BomService._validate_bom(db, bom)
        if validation:
            raise errors.ConflictError(msg='BOM_VALIDATION_FAILED', data=validation)
        bom.status = BomStatus.ACTIVE
        return bom

    @staticmethod
    async def deactivate_bom(db: AsyncSession, bom_id: int) -> Bom:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_active(bom)
        bom.status = BomStatus.INACTIVE
        bom.is_default = False
        return bom

    @staticmethod
    async def set_default_bom(db: AsyncSession, bom_id: int) -> Bom:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_active(bom)
        candidates = await db.scalars(
            select(Bom).where(
                Bom.product_material_id == bom.product_material_id,
                Bom.deleted == 0,
                Bom.id != bom.id,
                Bom.is_default.is_(True),
            )
        )
        for candidate in candidates:
            candidate.is_default = False
        bom.is_default = True
        return bom

    @staticmethod
    async def _active_boms_for_product(
        db: AsyncSession, product_material_id: int, production_date: datetime | None
    ) -> list[Bom]:
        effective_date = production_date or timezone.now()
        statement = (
            select(Bom)
            .where(
                Bom.product_material_id == product_material_id,
                Bom.status == BomStatus.ACTIVE,
                Bom.deleted == 0,
                Bom.effective_from.is_(None) | (Bom.effective_from <= effective_date),
                Bom.effective_to.is_(None) | (Bom.effective_to >= effective_date),
            )
            .order_by(Bom.is_default.desc(), Bom.effective_from.desc(), Bom.id.desc())
        )
        return list((await db.scalars(statement)).all())

    @staticmethod
    async def list_options(
        db: AsyncSession, product_material_id: int, production_date: datetime | None
    ) -> list[BomOption]:
        await BomService._require_product(db, product_material_id)
        return [
            BomOption(
                id=bom.id,
                bom_code=bom.bom_code,
                bom_version=bom.bom_version,
                status=bom.status,
                effective_from=bom.effective_from,
                effective_to=bom.effective_to,
                is_default=bom.is_default,
            )
            for bom in await BomService._active_boms_for_product(db, product_material_id, production_date)
        ]

    @staticmethod
    async def get_default(
        db: AsyncSession, product_material_id: int, production_date: datetime | None
    ) -> BomOption:
        options = await BomService.list_options(db, product_material_id, production_date)
        default = next((option for option in options if option.is_default), None)
        if not default:
            raise errors.NotFoundError(msg='BOM_DEFAULT_NOT_FOUND')
        return default

    @staticmethod
    async def _select_child_bom(
        db: AsyncSession, material_id: int, production_date: datetime | None
    ) -> Bom | None:
        boms = await BomService._active_boms_for_product(db, material_id, production_date)
        return boms[0] if boms else None

    @staticmethod
    async def get_tree(db: AsyncSession, bom_id: int) -> BomTree:
        bom = await BomService._require_bom(db, bom_id)
        product = await BomService._require_product(db, bom.product_material_id)
        units = await BomService._unit_map(db, {product.base_unit_id})
        path = {product.id}

        async def build_children(current_bom: Bom, current_path: set[int], depth: int) -> list[BomTreeNode]:
            if depth > BomService.max_tree_depth:
                raise errors.ConflictError(msg='BOM_CYCLE_DETECTED')
            items = list(await bom_repo.get_items(db, current_bom.id))
            materials = await BomService._material_map(db, {item.component_material_id for item in items})
            item_units = await BomService._unit_map(db, {item.unit_id for item in items})
            nodes = []
            for item in items:
                component = materials.get(item.component_material_id)
                if not component:
                    raise errors.NotFoundError(msg='BOM_COMPONENT_NOT_FOUND')
                if component.id in current_path:
                    raise errors.ConflictError(msg='BOM_CYCLE_DETECTED')
                child_bom = await BomService._select_child_bom(db, component.id, None)
                children = (
                    await build_children(child_bom, {*current_path, component.id}, depth + 1)
                    if child_bom
                    else []
                )
                nodes.append(
                    BomTreeNode(
                        material_id=component.id,
                        material_code=component.material_code,
                        material_name=component.material_name,
                        specification=component.specification,
                        quantity=item.quantity,
                        unit=item_units.get(item.unit_id).unit_code if item_units.get(item.unit_id) else '',
                        line_no=item.line_no,
                        loss_rate=item.loss_rate,
                        fixed_loss_qty=item.fixed_loss_qty,
                        is_optional=item.is_optional,
                        children=children,
                    )
                )
            return nodes

        return BomTree(
            bom_id=bom.id,
            bom_code=bom.bom_code,
            bom_version=bom.bom_version,
            material_id=product.id,
            material_code=product.material_code,
            material_name=product.material_name,
            quantity=Decimal('1'),
            unit=units.get(product.base_unit_id).unit_code if units.get(product.base_unit_id) else '',
            children=await build_children(bom, path, 1),
        )

    @staticmethod
    def _requirement(
        item: BomItem, material: Material, unit: UnitOfMeasure, production_quantity: Decimal, base_quantity: Decimal
    ) -> MaterialRequirement:
        standard = production_quantity / base_quantity * item.quantity
        planned = standard * (Decimal('1') + item.loss_rate / Decimal('100')) + item.fixed_loss_qty
        return MaterialRequirement(
            material_id=material.id,
            material_code=material.material_code,
            material_name=material.material_name,
            standard_required_qty=standard,
            loss_rate=item.loss_rate,
            fixed_loss_qty=item.fixed_loss_qty,
            planned_required_qty=planned,
            unit=unit.unit_code,
            is_optional=item.is_optional,
        )

    @staticmethod
    async def calculate(db: AsyncSession, bom_id: int, obj: CalculateBomParam) -> list[MaterialRequirement]:
        bom = await BomService._require_bom(db, bom_id)
        await BomService._ensure_active(bom)
        if obj.production_date and not (
            (bom.effective_from is None or bom.effective_from <= obj.production_date)
            and (bom.effective_to is None or bom.effective_to >= obj.production_date)
        ):
            raise errors.ConflictError(msg='BOM_INVALID_EFFECTIVE_DATE')
        items = list(await bom_repo.get_items(db, bom.id))
        materials = await BomService._material_map(db, {item.component_material_id for item in items})
        units = await BomService._unit_map(db, {item.unit_id for item in items})
        if not obj.explode:
            return [
                BomService._requirement(item, materials[item.component_material_id], units[item.unit_id], obj.production_quantity, bom.base_quantity)
                for item in items
                if item.component_material_id in materials and item.unit_id in units
            ]

        aggregate: dict[int, MaterialRequirement] = {}
        active_path: set[int] = {bom.product_material_id}

        async def expand(current_bom: Bom, production_quantity: Decimal, path: set[int]) -> None:
            current_items = list(await bom_repo.get_items(db, current_bom.id))
            current_materials = await BomService._material_map(db, {item.component_material_id for item in current_items})
            current_units = await BomService._unit_map(db, {item.unit_id for item in current_items})
            for current_item in current_items:
                component = current_materials.get(current_item.component_material_id)
                unit = current_units.get(current_item.unit_id)
                if not component or not unit:
                    continue
                requirement = BomService._requirement(
                    current_item, component, unit, production_quantity, current_bom.base_quantity
                )
                child_bom = await BomService._select_child_bom(db, component.id, obj.production_date)
                if child_bom:
                    if component.id in path:
                        raise errors.ConflictError(msg='BOM_CYCLE_DETECTED')
                    await expand(child_bom, requirement.planned_required_qty, {*path, component.id})
                    continue
                existing = aggregate.get(component.id)
                if existing:
                    existing.standard_required_qty += requirement.standard_required_qty
                    existing.planned_required_qty += requirement.planned_required_qty
                else:
                    aggregate[component.id] = requirement

        await expand(bom, obj.production_quantity, active_path)
        return list(aggregate.values())

    @staticmethod
    async def compare(db: AsyncSession, source_bom_id: int, target_bom_id: int) -> BomCompareResult:
        source = await BomService._require_bom(db, source_bom_id)
        target = await BomService._require_bom(db, target_bom_id)
        if source.product_material_id != target.product_material_id:
            raise errors.ConflictError(msg='BOM_COMPARE_PRODUCT_MISMATCH')
        source_items = {item.component_material_id: item for item in await bom_repo.get_items(db, source.id)}
        target_items = {item.component_material_id: item for item in await bom_repo.get_items(db, target.id)}
        material_map = await BomService._material_map(db, set(source_items) | set(target_items))
        changes: list[BomCompareChange] = []
        for material_id in sorted(set(source_items) | set(target_items)):
            before = source_items.get(material_id)
            after = target_items.get(material_id)
            material = material_map.get(material_id)
            if not material:
                continue
            if before is None:
                change_type = 'ADDED'
            elif after is None:
                change_type = 'REMOVED'
            elif before.quantity != after.quantity or before.loss_rate != after.loss_rate:
                change_type = 'CHANGED'
            else:
                continue
            changes.append(
                BomCompareChange(
                    change_type=change_type,
                    component_material_id=material_id,
                    component_code=material.material_code,
                    component_name=material.material_name,
                    source_quantity=before.quantity if before else None,
                    target_quantity=after.quantity if after else None,
                    source_loss_rate=before.loss_rate if before else None,
                    target_loss_rate=after.loss_rate if after else None,
                )
            )
        return BomCompareResult(source_bom_id=source.id, target_bom_id=target.id, changes=changes)


bom_service = BomService()
