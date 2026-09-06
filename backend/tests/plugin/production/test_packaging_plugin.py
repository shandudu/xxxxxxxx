from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.production.api.v1.mes.packaging import router
from backend.plugin.production.model import (
    PackagingHandlingUnit, PackagingHandlingUnitContent, PackagingInspection,
    PackagingLabelPrint, PackagingSpecification, PackagingTask, PackagingWeightRecord,
)
from backend.plugin.production.schema.packaging import (
    CreatePackagingSpecification, RecordPackagingWeight, ScanPackagingItem,
)


def test_packaging_models_cover_traceable_business_documents() -> None:
    assert {
        PackagingSpecification.__tablename__, PackagingTask.__tablename__,
        PackagingHandlingUnit.__tablename__, PackagingHandlingUnitContent.__tablename__,
        PackagingWeightRecord.__tablename__, PackagingInspection.__tablename__,
        PackagingLabelPrint.__tablename__,
    } == {
        'mes_packaging_specification', 'mes_packaging_task', 'mes_packaging_handling_unit',
        'mes_packaging_hu_content', 'mes_packaging_weight_record',
        'mes_packaging_inspection', 'mes_packaging_label_print',
    }
    task_fks = {constraint.name for constraint in PackagingTask.__table__.foreign_key_constraints}
    assert {'fk_packaging_task_report', 'fk_packaging_task_stock_tx', 'fk_packaging_task_spec'} <= task_fks
    assert 'uk_packaging_content_scan_key' in {
        constraint.name for constraint in PackagingHandlingUnitContent.__table__.constraints
    }


def test_packaging_api_exposes_complete_workflow() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}
    assert len(router.routes) == 18
    for expected in (
        ('/specifications', frozenset({'POST'})),
        ('/tasks', frozenset({'POST'})),
        ('/tasks/{task_id}/release', frozenset({'POST'})),
        ('/tasks/{task_id}/handling-units', frozenset({'POST'})),
        ('/handling-units/{hu_id}/scan', frozenset({'POST'})),
        ('/handling-units/{hu_id}/weight', frozenset({'POST'})),
        ('/handling-units/{hu_id}/seal', frozenset({'POST'})),
        ('/handling-units/{hu_id}/inspection', frozenset({'POST'})),
        ('/handling-units/{hu_id}/labels', frozenset({'POST'})),
        ('/tasks/{task_id}/release-to-stock', frozenset({'POST'})),
    ):
        assert expected in endpoints


def test_packaging_weight_spec_requires_target_and_tolerance() -> None:
    with pytest.raises(ValidationError, match='WEIGHT_TARGET_AND_TOLERANCE_REQUIRED'):
        CreatePackagingSpecification(
            spec_code='PKG-01', spec_name='Carton', material_id=1,
            units_per_carton=Decimal('10'), require_weight_check=True,
        )


def test_packaging_scan_and_weight_request_guards() -> None:
    with pytest.raises(ValidationError):
        ScanPackagingItem(code='LOT-1', idempotency_key='short', quantity=Decimal('1'))
    with pytest.raises(ValidationError, match='GROSS_WEIGHT_MUST_EXCEED_TARE_WEIGHT'):
        RecordPackagingWeight(
            gross_weight=Decimal('2'), tare_weight=Decimal('2'),
            idempotency_key='WEIGHT:12345678',
        )
