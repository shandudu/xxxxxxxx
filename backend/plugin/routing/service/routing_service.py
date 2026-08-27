from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.common.pagination import paging_data
from backend.plugin.material.crud.material import material_repo
from backend.plugin.material.enums import CategoryStatus, MaterialStatus
from backend.plugin.material.model import Material, UnitOfMeasure
from backend.plugin.routing.crud.routing import routing_repo
from backend.plugin.routing.enums import (
    OperationStatus,
    OperationType,
    RoutingStatus,
    RoutingType,
    RunTimeUnit,
    WorkCenterStatus,
    WorkCenterType,
)
from backend.plugin.routing.model import Operation, Routing, RoutingOperation, WorkCenter
from backend.plugin.routing.schema.routing import (
    ActivateRoutingParam,
    CalculateRoutingTimeParam,
    CopyRoutingParam,
    CreateOperationParam,
    CreateRoutingOperationParam,
    CreateRoutingParam,
    CreateWorkCenterParam,
    MaterialSummary,
    OperationDetail,
    OperationListItem,
    OperationOption,
    OperationSummary,
    ReorderRoutingOperationParam,
    RoutingDetail,
    RoutingListItem,
    RoutingOperationDetail,
    RoutingOption,
    RoutingTimeCalculation,
    RoutingTimeItem,
    RoutingValidationIssue,
    RoutingValidationResult,
    UpdateOperationParam,
    UpdateRoutingOperationParam,
    UpdateRoutingParam,
    UpdateWorkCenterParam,
    WorkCenterDetail,
    WorkCenterOption,
    WorkCenterSummary,
)
from backend.utils.timezone import timezone


class RoutingService:
    @staticmethod
    async def _require_operation(db: AsyncSession, operation_id: int, active_only: bool = False) -> Operation:
        item = await routing_repo.get_operation(db, operation_id)
        if not item:
            raise errors.NotFoundError(msg='OPERATION_NOT_FOUND')
        if active_only and item.status != OperationStatus.ACTIVE:
            raise errors.ConflictError(msg='OPERATION_DISABLED')
        return item

    @staticmethod
    async def _require_work_center(db: AsyncSession, work_center_id: int, active_only: bool = False) -> WorkCenter:
        item = await routing_repo.get_work_center(db, work_center_id)
        if not item:
            raise errors.NotFoundError(msg='WORK_CENTER_NOT_FOUND')
        if active_only and (item.status != WorkCenterStatus.ACTIVE or not item.production_enabled):
            raise errors.ConflictError(msg='WORK_CENTER_DISABLED')
        return item

    @staticmethod
    async def _require_routing(db: AsyncSession, routing_id: int) -> Routing:
        item = await routing_repo.get_routing(db, routing_id)
        if not item:
            raise errors.NotFoundError(msg='ROUTING_NOT_FOUND')
        return item

    @staticmethod
    async def _require_product(db: AsyncSession, material_id: int) -> Material:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='ROUTING_PRODUCT_NOT_FOUND')
        if material.status != MaterialStatus.ACTIVE:
            raise errors.ConflictError(msg='ROUTING_PRODUCT_DISABLED')
        if not material.producible:
            raise errors.ConflictError(msg='ROUTING_PRODUCT_NOT_PRODUCIBLE')
        return material

    @staticmethod
    async def _ensure_draft(routing: Routing) -> None:
        if routing.status != RoutingStatus.DRAFT:
            raise errors.ConflictError(msg='ROUTING_NOT_DRAFT')

    @staticmethod
    async def _ensure_active(routing: Routing) -> None:
        if routing.status != RoutingStatus.ACTIVE:
            raise errors.ConflictError(msg='ROUTING_NOT_ACTIVE')

    @staticmethod
    def _operation_summary(item: Operation) -> OperationSummary:
        return OperationSummary(
            id=item.id,
            code=item.operation_code,
            name=item.operation_name,
            status=item.status,
            operation_type=item.operation_type,
        )

    @staticmethod
    def _work_center_summary(item: WorkCenter) -> WorkCenterSummary:
        return WorkCenterSummary(
            id=item.id,
            code=item.work_center_code,
            name=item.work_center_name,
            status=item.status,
            production_enabled=item.production_enabled,
        )

    @staticmethod
    async def _operation_map(db: AsyncSession, operation_ids: set[int]) -> dict[int, Operation]:
        if not operation_ids:
            return {}
        result = await db.scalars(select(Operation).where(Operation.id.in_(operation_ids), Operation.deleted == 0))
        return {item.id: item for item in result}

    @staticmethod
    async def _work_center_map(db: AsyncSession, work_center_ids: set[int]) -> dict[int, WorkCenter]:
        if not work_center_ids:
            return {}
        result = await db.scalars(select(WorkCenter).where(WorkCenter.id.in_(work_center_ids), WorkCenter.deleted == 0))
        return {item.id: item for item in result}

    @staticmethod
    async def _material_summary(db: AsyncSession, material_id: int) -> MaterialSummary:
        material = await material_repo.get_material(db, material_id)
        if not material:
            raise errors.NotFoundError(msg='ROUTING_PRODUCT_NOT_FOUND')
        unit = await material_repo.get_unit(db, material.base_unit_id)
        return MaterialSummary(
            id=material.id,
            code=material.material_code,
            name=material.material_name,
            specification=material.specification,
            unit=unit.unit_code if unit else '',
        )

    @staticmethod
    async def _routing_operation_detail(
        db: AsyncSession,
        item: RoutingOperation,
        operations: dict[int, Operation] | None = None,
        work_centers: dict[int, WorkCenter] | None = None,
    ) -> RoutingOperationDetail:
        operations = operations or await RoutingService._operation_map(db, {item.operation_id})
        work_centers = work_centers or await RoutingService._work_center_map(
            db, {item.work_center_id} if item.work_center_id else set()
        )
        operation = operations.get(item.operation_id)
        if not operation:
            raise errors.NotFoundError(msg='OPERATION_NOT_FOUND')
        work_center = work_centers.get(item.work_center_id) if item.work_center_id else None
        return RoutingOperationDetail(
            id=item.id,
            routing_id=item.routing_id,
            sequence_no=item.sequence_no,
            operation_id=item.operation_id,
            work_center_id=item.work_center_id,
            operation_name_override=item.operation_name_override,
            operation_name_snapshot=item.operation_name_snapshot,
            operation_display_name=item.operation_name_override or item.operation_name_snapshot or operation.operation_name,
            setup_time_min=item.setup_time_min,
            run_time_value=item.run_time_value,
            run_time_unit=item.run_time_unit,
            queue_time_min=item.queue_time_min,
            move_time_min=item.move_time_min,
            standard_yield_rate=item.standard_yield_rate,
            reporting_required=item.reporting_required,
            quality_required=item.quality_required,
            trace_required=item.trace_required,
            remark=item.remark,
            sort_no=item.sort_no,
            operation=RoutingService._operation_summary(operation),
            work_center=RoutingService._work_center_summary(work_center) if work_center else None,
            created_time=item.created_time,
            updated_time=item.updated_time,
        )

    @staticmethod
    async def list_routing_operations(db: AsyncSession, routing_id: int) -> list[RoutingOperationDetail]:
        await RoutingService._require_routing(db, routing_id)
        items = list(await routing_repo.get_operations(db, routing_id))
        operations = await RoutingService._operation_map(db, {item.operation_id for item in items})
        work_centers = await RoutingService._work_center_map(
            db, {item.work_center_id for item in items if item.work_center_id}
        )
        return [
            await RoutingService._routing_operation_detail(db, item, operations, work_centers) for item in items
        ]

    @staticmethod
    async def _routing_item(
        db: AsyncSession,
        routing: Routing,
        with_operations: bool = False,
        operation_count: int | None = None,
    ) -> RoutingListItem | RoutingDetail:
        if operation_count is None:
            operation_count = (await routing_repo.get_operation_count_map(db, {routing.id})).get(routing.id, 0)
        data = dict(
            id=routing.id,
            routing_code=routing.routing_code,
            routing_name=routing.routing_name,
            product_material_id=routing.product_material_id,
            routing_version=routing.routing_version,
            routing_type=routing.routing_type,
            base_quantity=routing.base_quantity,
            status=routing.status,
            effective_from=routing.effective_from,
            effective_to=routing.effective_to,
            is_default=routing.is_default,
            description=routing.description,
            remark=routing.remark,
            product=await RoutingService._material_summary(db, routing.product_material_id),
            operation_count=operation_count,
            created_time=routing.created_time,
            updated_time=routing.updated_time,
        )
        if not with_operations:
            return RoutingListItem(**data)
        return RoutingDetail(operations=await RoutingService.list_routing_operations(db, routing.id), **data)

    @staticmethod
    async def create_operation(db: AsyncSession, obj: CreateOperationParam) -> Operation:
        if await routing_repo.get_operation_by_code(db, obj.operation_code):
            raise errors.ConflictError(msg='OPERATION_CODE_EXISTS')
        return await routing_repo.create_operation(db, {**obj.model_dump(), 'status': OperationStatus.ACTIVE})

    @staticmethod
    async def update_operation(db: AsyncSession, operation_id: int, obj: UpdateOperationParam) -> Operation:
        item = await RoutingService._require_operation(db, operation_id)
        if await routing_repo.get_operation_by_code(db, obj.operation_code, exclude_id=operation_id):
            raise errors.ConflictError(msg='OPERATION_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(item, key, value)
        return item

    @staticmethod
    async def get_operation(db: AsyncSession, operation_id: int) -> OperationDetail:
        item = await RoutingService._require_operation(db, operation_id)
        return OperationDetail.model_validate(item)

    @staticmethod
    async def list_operations(
        db: AsyncSession,
        keyword: str | None,
        operation_type: OperationType | None,
        status: OperationStatus | None,
    ) -> dict[str, Any]:
        page_data = await paging_data(db, await routing_repo.get_operation_select(keyword, operation_type, status))
        page_data['items'] = [OperationListItem.model_validate(item) for item in page_data['items']]
        return page_data

    @staticmethod
    async def update_operation_status(db: AsyncSession, operation_id: int, status: OperationStatus) -> Operation:
        item = await RoutingService._require_operation(db, operation_id)
        item.status = status
        return item

    @staticmethod
    async def list_operation_options(db: AsyncSession, keyword: str | None) -> list[OperationOption]:
        items = (
            await db.scalars(
                (await routing_repo.get_operation_select(keyword, None, OperationStatus.ACTIVE)).order_by(
                    Operation.sort_no, Operation.operation_code
                )
            )
        ).all()
        return [
            OperationOption(
                **RoutingService._operation_summary(item).model_dump(),
                operation_short_name=item.operation_short_name,
                quality_enabled=item.quality_enabled,
                trace_enabled=item.trace_enabled,
            )
            for item in items
        ]

    @staticmethod
    async def create_work_center(db: AsyncSession, obj: CreateWorkCenterParam) -> WorkCenter:
        if await routing_repo.get_work_center_by_code(db, obj.work_center_code):
            raise errors.ConflictError(msg='WORK_CENTER_CODE_EXISTS')
        return await routing_repo.create_work_center(db, {**obj.model_dump(), 'status': WorkCenterStatus.ACTIVE})

    @staticmethod
    async def update_work_center(db: AsyncSession, work_center_id: int, obj: UpdateWorkCenterParam) -> WorkCenter:
        item = await RoutingService._require_work_center(db, work_center_id)
        if await routing_repo.get_work_center_by_code(db, obj.work_center_code, exclude_id=work_center_id):
            raise errors.ConflictError(msg='WORK_CENTER_CODE_EXISTS')
        for key, value in obj.model_dump().items():
            setattr(item, key, value)
        return item

    @staticmethod
    async def get_work_center(db: AsyncSession, work_center_id: int) -> WorkCenterDetail:
        return WorkCenterDetail.model_validate(await RoutingService._require_work_center(db, work_center_id))

    @staticmethod
    async def list_work_centers(
        db: AsyncSession,
        keyword: str | None,
        work_center_type: WorkCenterType | None,
        status: WorkCenterStatus | None,
    ) -> dict[str, Any]:
        page_data = await paging_data(db, await routing_repo.get_work_center_select(keyword, work_center_type, status))
        page_data['items'] = [WorkCenterDetail.model_validate(item) for item in page_data['items']]
        return page_data

    @staticmethod
    async def update_work_center_status(
        db: AsyncSession, work_center_id: int, status: WorkCenterStatus
    ) -> WorkCenter:
        item = await RoutingService._require_work_center(db, work_center_id)
        item.status = status
        return item

    @staticmethod
    async def list_work_center_options(db: AsyncSession, keyword: str | None) -> list[WorkCenterOption]:
        items = (
            await db.scalars(
                (await routing_repo.get_work_center_select(keyword, None, WorkCenterStatus.ACTIVE))
                .where(WorkCenter.production_enabled.is_(True))
                .order_by(WorkCenter.sort_no, WorkCenter.work_center_code)
            )
        ).all()
        return [
            WorkCenterOption(
                **RoutingService._work_center_summary(item).model_dump(),
                work_center_type=item.work_center_type,
                factory_code=item.factory_code,
                workshop_code=item.workshop_code,
            )
            for item in items
        ]

    @staticmethod
    async def create_routing(db: AsyncSession, obj: CreateRoutingParam) -> Routing:
        if await routing_repo.get_routing_by_code(db, obj.routing_code):
            raise errors.ConflictError(msg='ROUTING_CODE_EXISTS')
        if await routing_repo.get_routing_by_product_version(
            db, obj.product_material_id, obj.routing_version, obj.routing_type
        ):
            raise errors.ConflictError(msg='ROUTING_VERSION_EXISTS')
        await RoutingService._require_product(db, obj.product_material_id)
        return await routing_repo.create_routing(
            db, {**obj.model_dump(), 'status': RoutingStatus.DRAFT, 'is_default': False}
        )

    @staticmethod
    async def update_routing(db: AsyncSession, routing_id: int, obj: UpdateRoutingParam) -> Routing:
        item = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(item)
        if await routing_repo.get_routing_by_code(db, obj.routing_code, exclude_id=routing_id):
            raise errors.ConflictError(msg='ROUTING_CODE_EXISTS')
        if await routing_repo.get_routing_by_product_version(
            db, obj.product_material_id, obj.routing_version, obj.routing_type, exclude_id=routing_id
        ):
            raise errors.ConflictError(msg='ROUTING_VERSION_EXISTS')
        await RoutingService._require_product(db, obj.product_material_id)
        for key, value in obj.model_dump().items():
            setattr(item, key, value)
        return item

    @staticmethod
    async def get_routing(db: AsyncSession, routing_id: int) -> RoutingDetail:
        return await RoutingService._routing_item(
            db, await RoutingService._require_routing(db, routing_id), with_operations=True
        )  # type: ignore[return-value]

    @staticmethod
    async def list_routings(
        db: AsyncSession,
        keyword: str | None,
        product_material_id: int | None,
        status: RoutingStatus | None,
        routing_type: RoutingType | None,
        is_default: bool | None,
        effective_date: datetime | None,
    ) -> dict[str, Any]:
        page_data = await paging_data(
            db,
            await routing_repo.get_routing_select(
                keyword, product_material_id, status, routing_type, is_default, effective_date
            ),
        )
        count_map = await routing_repo.get_operation_count_map(db, {item.id for item in page_data['items']})
        page_data['items'] = [
            await RoutingService._routing_item(db, item, operation_count=count_map.get(item.id, 0))
            for item in page_data['items']
        ]
        return page_data

    @staticmethod
    async def _routing_operation_data(
        db: AsyncSession, obj: CreateRoutingOperationParam | UpdateRoutingOperationParam
    ) -> dict[str, Any]:
        operation = await RoutingService._require_operation(db, obj.operation_id, active_only=True)
        if obj.work_center_id:
            await RoutingService._require_work_center(db, obj.work_center_id, active_only=True)
        return {**obj.model_dump(), 'operation_name_snapshot': operation.operation_name}

    @staticmethod
    async def add_routing_operation(
        db: AsyncSession, routing_id: int, obj: CreateRoutingOperationParam
    ) -> RoutingOperationDetail:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(routing)
        if await routing_repo.get_routing_operation_by_sequence(db, routing_id, obj.sequence_no):
            raise errors.ConflictError(msg='ROUTING_SEQUENCE_DUPLICATED')
        item = await routing_repo.create_routing_operation(
            db, {'routing_id': routing_id, **(await RoutingService._routing_operation_data(db, obj))}
        )
        return await RoutingService._routing_operation_detail(db, item)

    @staticmethod
    async def update_routing_operation(
        db: AsyncSession,
        routing_id: int,
        routing_operation_id: int,
        obj: UpdateRoutingOperationParam,
    ) -> RoutingOperationDetail:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(routing)
        item = await routing_repo.get_routing_operation(db, routing_id, routing_operation_id)
        if not item:
            raise errors.NotFoundError(msg='ROUTING_OPERATION_NOT_FOUND')
        if await routing_repo.get_routing_operation_by_sequence(
            db, routing_id, obj.sequence_no, exclude_id=routing_operation_id
        ):
            raise errors.ConflictError(msg='ROUTING_SEQUENCE_DUPLICATED')
        for key, value in (await RoutingService._routing_operation_data(db, obj)).items():
            setattr(item, key, value)
        return await RoutingService._routing_operation_detail(db, item)

    @staticmethod
    async def delete_routing_operation(db: AsyncSession, routing_id: int, routing_operation_id: int) -> None:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(routing)
        item = await routing_repo.get_routing_operation(db, routing_id, routing_operation_id)
        if not item:
            raise errors.NotFoundError(msg='ROUTING_OPERATION_NOT_FOUND')
        item.deleted = item.id
        item.deleted_time = timezone.now()

    @staticmethod
    async def reorder_routing_operations(
        db: AsyncSession, routing_id: int, obj: ReorderRoutingOperationParam
    ) -> list[RoutingOperationDetail]:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(routing)
        items = list(await routing_repo.get_operations(db, routing_id))
        requested = {entry.routing_operation_id: entry for entry in obj.items}
        if len(items) != len(requested) or {item.id for item in items} != set(requested):
            raise errors.ConflictError(msg='ROUTING_REORDER_INCOMPLETE')
        for item in items:
            item.sequence_no = -item.id
        await db.flush()
        for item in items:
            request_item = requested[item.id]
            item.sequence_no = request_item.sequence_no
            item.sort_no = request_item.sequence_no
        return await RoutingService.list_routing_operations(db, routing_id)

    @staticmethod
    def _issue(code: str, message: str) -> RoutingValidationIssue:
        return RoutingValidationIssue(code=code, message=message)

    @staticmethod
    async def _validate_routing(db: AsyncSession, routing: Routing) -> list[RoutingValidationIssue]:
        validation_errors: list[RoutingValidationIssue] = []
        product = await material_repo.get_material(db, routing.product_material_id)
        if not product:
            validation_errors.append(RoutingService._issue('ROUTING_PRODUCT_NOT_FOUND', '产品物料不存在'))
        else:
            if product.status != MaterialStatus.ACTIVE:
                validation_errors.append(RoutingService._issue('ROUTING_PRODUCT_DISABLED', '产品物料已停用'))
            if not product.producible:
                validation_errors.append(RoutingService._issue('ROUTING_PRODUCT_NOT_PRODUCIBLE', '产品物料不可生产'))
        if routing.base_quantity <= 0:
            validation_errors.append(RoutingService._issue('ROUTING_BASE_QUANTITY_INVALID', '基准数量必须大于零'))
        if routing.effective_from and routing.effective_to and routing.effective_from > routing.effective_to:
            validation_errors.append(RoutingService._issue('ROUTING_EFFECTIVE_DATE_INVALID', '有效期起始时间不能晚于结束时间'))

        items = list(await routing_repo.get_operations(db, routing.id))
        if not items:
            validation_errors.append(RoutingService._issue('ROUTING_OPERATION_EMPTY', '至少需要配置一道工序'))
            return validation_errors
        sequence_numbers: set[int] = set()
        operations = await RoutingService._operation_map(db, {item.operation_id for item in items})
        work_centers = await RoutingService._work_center_map(
            db, {item.work_center_id for item in items if item.work_center_id}
        )
        for item in items:
            if item.sequence_no < 1:
                validation_errors.append(RoutingService._issue('ROUTING_SEQUENCE_INVALID', '工序顺序必须大于零'))
            if item.sequence_no in sequence_numbers:
                validation_errors.append(RoutingService._issue('ROUTING_SEQUENCE_DUPLICATED', '工序顺序不能重复'))
            sequence_numbers.add(item.sequence_no)
            operation = operations.get(item.operation_id)
            if not operation:
                validation_errors.append(RoutingService._issue('ROUTING_OPERATION_NOT_FOUND', '工序不存在'))
            elif operation.status != OperationStatus.ACTIVE:
                validation_errors.append(RoutingService._issue('ROUTING_OPERATION_DISABLED', f'工序 {operation.operation_code} 已停用'))
            if item.work_center_id:
                work_center = work_centers.get(item.work_center_id)
                if not work_center:
                    validation_errors.append(RoutingService._issue('ROUTING_WORK_CENTER_NOT_FOUND', '工作中心不存在'))
                elif work_center.status != WorkCenterStatus.ACTIVE or not work_center.production_enabled:
                    validation_errors.append(
                        RoutingService._issue('ROUTING_WORK_CENTER_DISABLED', f'工作中心 {work_center.work_center_code} 不可用于生产')
                    )
            if any(value < 0 for value in (item.setup_time_min, item.run_time_value, item.queue_time_min, item.move_time_min)):
                validation_errors.append(RoutingService._issue('ROUTING_TIME_INVALID', '标准时间不能为负数'))
            if not Decimal('0') < item.standard_yield_rate <= Decimal('100'):
                validation_errors.append(RoutingService._issue('ROUTING_YIELD_INVALID', '标准良率必须大于零且不超过100'))
        unique_errors: dict[tuple[str, str], RoutingValidationIssue] = {
            (item.code, item.message): item for item in validation_errors
        }
        return list(unique_errors.values())

    @staticmethod
    async def validate_routing(db: AsyncSession, routing_id: int) -> RoutingValidationResult:
        routing = await RoutingService._require_routing(db, routing_id)
        validation_errors = await RoutingService._validate_routing(db, routing)
        return RoutingValidationResult(valid=not validation_errors, errors=validation_errors)

    @staticmethod
    async def set_default_routing(db: AsyncSession, routing_id: int) -> Routing:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_active(routing)
        candidates = await db.scalars(
            select(Routing).where(
                Routing.product_material_id == routing.product_material_id,
                Routing.routing_type == routing.routing_type,
                Routing.deleted == 0,
                Routing.id != routing.id,
                Routing.is_default.is_(True),
            )
        )
        for candidate in candidates:
            candidate.is_default = False
        routing.is_default = True
        return routing

    @staticmethod
    async def activate_routing(
        db: AsyncSession, routing_id: int, obj: ActivateRoutingParam
    ) -> Routing:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_draft(routing)
        validation_errors = await RoutingService._validate_routing(db, routing)
        if validation_errors:
            raise errors.ConflictError(msg='ROUTING_VALIDATION_FAILED', data=[item.model_dump() for item in validation_errors])
        routing.status = RoutingStatus.ACTIVE
        if obj.set_as_default:
            await RoutingService.set_default_routing(db, routing_id)
        return routing

    @staticmethod
    async def deactivate_routing(db: AsyncSession, routing_id: int) -> Routing:
        routing = await RoutingService._require_routing(db, routing_id)
        await RoutingService._ensure_active(routing)
        routing.status = RoutingStatus.INACTIVE
        routing.is_default = False
        return routing

    @staticmethod
    async def copy_routing(db: AsyncSession, routing_id: int, obj: CopyRoutingParam) -> RoutingDetail:
        source = await RoutingService._require_routing(db, routing_id)
        if await routing_repo.get_routing_by_code(db, obj.new_routing_code):
            raise errors.ConflictError(msg='ROUTING_CODE_EXISTS')
        if await routing_repo.get_routing_by_product_version(
            db, source.product_material_id, obj.new_version, source.routing_type
        ):
            raise errors.ConflictError(msg='ROUTING_VERSION_EXISTS')
        copied = await routing_repo.create_routing(
            db,
            {
                'routing_code': obj.new_routing_code,
                'routing_name': obj.new_routing_name or source.routing_name,
                'product_material_id': source.product_material_id,
                'routing_version': obj.new_version,
                'routing_type': source.routing_type,
                'base_quantity': source.base_quantity,
                'status': RoutingStatus.DRAFT,
                'effective_from': obj.effective_from if obj.effective_from is not None else source.effective_from,
                'effective_to': obj.effective_to if obj.effective_to is not None else source.effective_to,
                'is_default': False,
                'description': obj.description if obj.description is not None else source.description,
                'remark': obj.remark if obj.remark is not None else source.remark,
            },
        )
        for item in await routing_repo.get_operations(db, source.id):
            await routing_repo.create_routing_operation(
                db,
                {
                    'routing_id': copied.id,
                    'sequence_no': item.sequence_no,
                    'operation_id': item.operation_id,
                    'work_center_id': item.work_center_id,
                    'operation_name_override': item.operation_name_override,
                    'operation_name_snapshot': item.operation_name_snapshot,
                    'setup_time_min': item.setup_time_min,
                    'run_time_value': item.run_time_value,
                    'run_time_unit': item.run_time_unit,
                    'queue_time_min': item.queue_time_min,
                    'move_time_min': item.move_time_min,
                    'standard_yield_rate': item.standard_yield_rate,
                    'reporting_required': item.reporting_required,
                    'quality_required': item.quality_required,
                    'trace_required': item.trace_required,
                    'remark': item.remark,
                    'sort_no': item.sort_no,
                },
            )
        return await RoutingService.get_routing(db, copied.id)

    @staticmethod
    async def list_routing_options(
        db: AsyncSession,
        product_material_id: int,
        routing_type: RoutingType,
        production_date: datetime | None,
    ) -> list[RoutingOption]:
        effective_date = production_date or timezone.now()
        items = (
            await db.scalars(
                select(Routing)
                .where(
                    Routing.product_material_id == product_material_id,
                    Routing.routing_type == routing_type,
                    Routing.status == RoutingStatus.ACTIVE,
                    Routing.deleted == 0,
                    (Routing.effective_from.is_(None)) | (Routing.effective_from <= effective_date),
                    (Routing.effective_to.is_(None)) | (Routing.effective_to >= effective_date),
                )
                .order_by(Routing.is_default.desc(), Routing.effective_from.desc(), Routing.id.desc())
            )
        ).all()
        return [
            RoutingOption(
                id=item.id,
                code=item.routing_code,
                name=item.routing_name,
                version=item.routing_version,
                routing_type=item.routing_type,
                is_default=item.is_default,
            )
            for item in items
        ]

    @staticmethod
    async def get_default_routing(
        db: AsyncSession,
        product_material_id: int,
        routing_type: RoutingType,
        production_date: datetime | None,
    ) -> RoutingOption | None:
        options = await RoutingService.list_routing_options(db, product_material_id, routing_type, production_date)
        return next((item for item in options if item.is_default), None)

    @staticmethod
    def _run_time_in_minutes(value: Decimal, unit: RunTimeUnit) -> Decimal:
        if unit == RunTimeUnit.HOUR_PER_BASE_QTY:
            return value * Decimal('60')
        if unit == RunTimeUnit.SEC_PER_BASE_QTY:
            return value / Decimal('60')
        return value

    @staticmethod
    async def calculate_time(
        db: AsyncSession, routing_id: int, obj: CalculateRoutingTimeParam
    ) -> RoutingTimeCalculation:
        routing = await RoutingService._require_routing(db, routing_id)
        items = await RoutingService.list_routing_operations(db, routing_id)
        ratio = obj.production_quantity / routing.base_quantity
        result_items: list[RoutingTimeItem] = []
        total = Decimal('0')
        for item in items:
            run_time = RoutingService._run_time_in_minutes(item.run_time_value, item.run_time_unit) * ratio
            item_total = item.setup_time_min + run_time + item.queue_time_min + item.move_time_min
            total += item_total
            result_items.append(
                RoutingTimeItem(
                    routing_operation_id=item.id,
                    sequence_no=item.sequence_no,
                    operation_name=item.operation_display_name,
                    setup_time_min=item.setup_time_min,
                    run_time_min=run_time,
                    queue_time_min=item.queue_time_min,
                    move_time_min=item.move_time_min,
                    total_time_min=item_total,
                )
            )
        return RoutingTimeCalculation(
            routing_id=routing.id,
            production_quantity=obj.production_quantity,
            base_quantity=routing.base_quantity,
            total_time_min=total,
            items=result_items,
        )


routing_service = RoutingService()
