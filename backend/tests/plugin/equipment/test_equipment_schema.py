import asyncio
from types import SimpleNamespace

import pytest

from backend.common.exception import errors
from backend.plugin.equipment.enums import EquipmentCategoryStatus, EquipmentStatus
from backend.plugin.equipment.schema.equipment import (
    CreateEquipmentCategoryParam,
    CreateEquipmentParam,
    UpdateEquipmentCategoryParam,
)
from backend.plugin.equipment.service import equipment_service as equipment_service_module
from backend.plugin.equipment.service.equipment_service import EquipmentService


def test_equipment_code_is_trimmed_and_uppercased() -> None:
    equipment = CreateEquipmentParam(
        equipment_code=' coater-01 ',
        equipment_name='涂布机',
        category_id=1,
        equipment_type='PRODUCTION',
    )

    assert equipment.equipment_code == 'COATER-01'


def test_equipment_code_rejects_unsupported_characters() -> None:
    with pytest.raises(ValueError):
        CreateEquipmentParam(
            equipment_code='COATER/01',
            equipment_name='涂布机',
            category_id=1,
            equipment_type='PRODUCTION',
        )


def test_equipment_capacity_and_feature_switches_are_independent() -> None:
    equipment = CreateEquipmentParam(
        equipment_code='COATER-01',
        equipment_name='涂布机',
        category_id=1,
        equipment_type='PRODUCTION',
        production_enabled=True,
        data_collection_enabled=True,
        maintenance_enabled=False,
        rated_capacity='80.000000',
        capacity_unit='M/MIN',
    )

    assert str(equipment.rated_capacity) == '80.000000'
    assert equipment.production_enabled is True
    assert equipment.data_collection_enabled is True
    assert equipment.maintenance_enabled is False


def test_equipment_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError):
        CreateEquipmentParam(
            equipment_code='COATER-01',
            equipment_name='涂布机',
            category_id=1,
            equipment_type='PRODUCTION',
            rated_capacity=-1,
        )


def test_category_code_is_trimmed_and_uppercased() -> None:
    category = CreateEquipmentCategoryParam(category_code=' coater ', category_name='涂布设备')

    assert category.category_code == 'COATER'


def test_disabled_equipment_is_created_with_disabled_status(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict = {}

    class FakeRepository:
        async def get_equipment_by_code(self, *_args, **_kwargs):
            return None

        async def get_category(self, _db, _category_id):
            return SimpleNamespace(status=EquipmentCategoryStatus.ACTIVE)

        async def create_equipment(self, _db, data):
            created.update(data)
            return SimpleNamespace(**data)

    monkeypatch.setattr(equipment_service_module, 'equipment_repo', FakeRepository())
    result = asyncio.run(
        EquipmentService.create_equipment(
            None,
            CreateEquipmentParam(
                equipment_code='coater-01',
                equipment_name='涂布机',
                category_id=1,
                equipment_type='PRODUCTION',
                enabled=False,
            ),
        )
    )

    assert result.status == EquipmentStatus.DISABLED
    assert created['status'] == EquipmentStatus.DISABLED


def test_disabled_equipment_cannot_receive_a_runtime_status(monkeypatch: pytest.MonkeyPatch) -> None:
    equipment = SimpleNamespace(enabled=False, status=EquipmentStatus.DISABLED)

    class FakeRepository:
        async def get_equipment(self, _db, _equipment_id):
            return equipment

    monkeypatch.setattr(equipment_service_module, 'equipment_repo', FakeRepository())

    with pytest.raises(errors.ConflictError):
        asyncio.run(EquipmentService.update_status(None, 1, EquipmentStatus.RUNNING))


def test_category_cycle_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    categories = {
        1: SimpleNamespace(id=1, parent_id=None),
        2: SimpleNamespace(id=2, parent_id=1, status=EquipmentCategoryStatus.ACTIVE),
    }

    class FakeRepository:
        async def get_category(self, _db, category_id):
            return categories.get(category_id)

        async def get_category_by_code(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(equipment_service_module, 'equipment_repo', FakeRepository())

    with pytest.raises(errors.ConflictError):
        asyncio.run(
            EquipmentService.update_category(
                None,
                1,
                UpdateEquipmentCategoryParam(
                    category_code='PRODUCTION',
                    category_name='生产设备',
                    parent_id=2,
                ),
            )
        )
