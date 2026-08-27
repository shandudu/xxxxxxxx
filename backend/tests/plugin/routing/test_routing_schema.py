import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.common.exception.errors import ConflictError
from backend.plugin.routing.enums import (
    OperationStatus,
    OperationType,
    RoutingStatus,
    RoutingType,
    RunTimeUnit,
    WorkCenterStatus,
    WorkCenterType,
)
from backend.plugin.routing.schema.routing import (
    CopyRoutingParam,
    CreateOperationParam,
    CreateRoutingOperationParam,
    CreateRoutingParam,
    CreateWorkCenterParam,
    ReorderRoutingOperationParam,
)
from backend.plugin.routing.service.routing_service import RoutingService, routing_repo


def test_master_data_codes_are_normalized_and_use_task_enums() -> None:
    operation = CreateOperationParam(operation_code=' op-coat ', operation_name=' 涂布 ')
    work_center = CreateWorkCenterParam(
        work_center_code=' wc-coat ', work_center_name=' 涂布工作中心 ', work_center_type='MACHINE_GROUP'
    )

    assert operation.operation_code == 'OP-COAT'
    assert operation.operation_name == '涂布'
    assert operation.operation_type == OperationType.PROCESS
    assert work_center.work_center_code == 'WC-COAT'
    assert work_center.work_center_type == WorkCenterType.MACHINE_GROUP
    assert OperationStatus.ACTIVE.value == 'ACTIVE'
    assert WorkCenterStatus.DISABLED.value == 'DISABLED'


def test_master_data_rejects_invalid_codes_and_parallel_capacity() -> None:
    with pytest.raises(ValueError):
        CreateOperationParam(operation_code='OP/COAT', operation_name='涂布')
    with pytest.raises(ValueError):
        CreateWorkCenterParam(
            work_center_code='WC-COAT', work_center_name='涂布工作中心', parallel_capacity=0
        )


def test_routing_has_type_base_quantity_and_effective_date_validation() -> None:
    routing = CreateRoutingParam(
        routing_code=' rt-fg-001-001 ',
        routing_name=' 电芯标准路线 ',
        product_material_id=1,
        routing_version=' v1.0 ',
        routing_type='STANDARD',
        base_quantity='100',
    )

    assert routing.routing_code == 'RT-FG-001-001'
    assert routing.routing_version == 'V1.0'
    assert routing.base_quantity == Decimal('100')
    assert routing.routing_type == RoutingType.STANDARD
    assert RoutingStatus.DRAFT.value == 'DRAFT'

    with pytest.raises(ValueError):
        CreateRoutingParam(
            routing_code='RT-1', routing_name='测试路线', product_material_id=1, routing_version='V1.0',
            effective_from='2026-08-02T00:00:00', effective_to='2026-08-01T00:00:00',
        )


def test_routing_operation_keeps_manufacturing_time_and_yield_precision() -> None:
    item = CreateRoutingOperationParam(
        sequence_no=10,
        operation_id=1,
        setup_time_min='30',
        run_time_value='20.5',
        run_time_unit='MIN_PER_BASE_QTY',
        queue_time_min='5',
        move_time_min='2.5',
        standard_yield_rate='99.5',
    )

    assert item.setup_time_min == Decimal('30')
    assert item.run_time_value == Decimal('20.5')
    assert item.run_time_unit == RunTimeUnit.MIN_PER_BASE_QTY
    assert item.standard_yield_rate == Decimal('99.5')

    with pytest.raises(ValueError):
        CreateRoutingOperationParam(sequence_no=10, operation_id=1, standard_yield_rate='0')


def test_reorder_requires_complete_unique_positions() -> None:
    request = ReorderRoutingOperationParam(
        items=[{'routing_operation_id': 10, 'sequence_no': 10}, {'routing_operation_id': 11, 'sequence_no': 20}]
    )
    assert [item.sequence_no for item in request.items] == [10, 20]
    with pytest.raises(ValueError):
        ReorderRoutingOperationParam(
            items=[{'routing_operation_id': 10, 'sequence_no': 10}, {'routing_operation_id': 10, 'sequence_no': 20}]
        )


def test_copy_param_normalizes_new_version() -> None:
    request = CopyRoutingParam(new_routing_code=' rt-fg-001-002 ', new_version=' v1.1 ')
    assert request.new_routing_code == 'RT-FG-001-002'
    assert request.new_version == 'V1.1'


def test_routing_operation_requires_active_master_data(monkeypatch: pytest.MonkeyPatch) -> None:
    operation = SimpleNamespace(status=OperationStatus.ACTIVE, operation_name='涂布')

    async def get_operation(*_args):
        return operation

    monkeypatch.setattr(routing_repo, 'get_operation', get_operation)
    data = asyncio.run(
        RoutingService._routing_operation_data(
            SimpleNamespace(), CreateRoutingOperationParam(sequence_no=20, operation_id=5)
        )
    )
    assert data['operation_name_snapshot'] == '涂布'

    async def get_disabled_operation(*_args):
        return SimpleNamespace(status=OperationStatus.DISABLED)

    monkeypatch.setattr(routing_repo, 'get_operation', get_disabled_operation)
    with pytest.raises(ConflictError, match='OPERATION_DISABLED'):
        asyncio.run(
            RoutingService._routing_operation_data(
                SimpleNamespace(), CreateRoutingOperationParam(sequence_no=10, operation_id=1)
            )
        )


def test_active_routing_is_not_editable_in_place() -> None:
    with pytest.raises(ConflictError, match='ROUTING_NOT_DRAFT'):
        asyncio.run(RoutingService._ensure_draft(SimpleNamespace(status=RoutingStatus.ACTIVE)))


def test_reorder_uses_temporary_sequences_before_swapping(monkeypatch: pytest.MonkeyPatch) -> None:
    first = SimpleNamespace(id=1, sequence_no=10, sort_no=10)
    second = SimpleNamespace(id=2, sequence_no=20, sort_no=20)

    async def require_routing(*_args):
        return SimpleNamespace(status=RoutingStatus.DRAFT)

    async def get_operations(*_args):
        return [first, second]

    async def list_operations(*_args):
        return ['reordered']

    class FakeSession:
        flush_count = 0

        async def flush(self) -> None:
            self.flush_count += 1
            assert {first.sequence_no, second.sequence_no} == {-1, -2}

    monkeypatch.setattr(RoutingService, '_require_routing', require_routing)
    monkeypatch.setattr(RoutingService, 'list_routing_operations', list_operations)
    monkeypatch.setattr(routing_repo, 'get_operations', get_operations)
    db = FakeSession()
    result = asyncio.run(
        RoutingService.reorder_routing_operations(
            db,
            1,
            ReorderRoutingOperationParam(
                items=[{'routing_operation_id': 2, 'sequence_no': 10}, {'routing_operation_id': 1, 'sequence_no': 20}]
            ),
        )
    )

    assert result == ['reordered']
    assert db.flush_count == 1
    assert (first.sequence_no, second.sequence_no) == (20, 10)
