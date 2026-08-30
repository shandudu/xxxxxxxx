import pytest
from pydantic import ValidationError

from backend.plugin.equipment.api.v1.mes.equipment import router
from backend.plugin.equipment.model import (
    MoldAsset, MoldCavity, MoldCavityQualityRecord, MoldCostLedger,
    MoldMaintenanceOrder, MoldMountRecord, MoldUsageRecord,
)
from backend.plugin.equipment.schema.mold import CreateCavityQuality, CreateMold


def test_mold_models_and_routes_are_registered() -> None:
    assert MoldAsset.__tablename__ == 'mes_mold_asset'
    assert MoldCavity.__tablename__ == 'mes_mold_cavity'
    assert MoldMountRecord.__tablename__ == 'mes_mold_mount_record'
    assert MoldUsageRecord.__tablename__ == 'mes_mold_usage_record'
    assert MoldMaintenanceOrder.__tablename__ == 'mes_mold_maintenance_order'
    assert MoldCavityQualityRecord.__tablename__ == 'mes_mold_cavity_quality_record'
    assert MoldCostLedger.__tablename__ == 'mes_mold_cost_ledger'
    paths = {route.path for route in router.routes}
    assert '/molds/{mold_id}/mount' in paths
    assert '/molds/maintenance/{order_id}/complete' in paths
    assert '/molds/{mold_id}/cost-analysis' in paths


def test_mold_payload_rules() -> None:
    with pytest.raises(ValidationError):
        CreateMold(
            mold_code='M-1', mold_name='Mold', tool_equipment_id=1, product_material_id=1,
            mold_type='INJECTION', cavity_count=2, designed_life_shots=100,
            maintenance_interval_shots=101,
        )
    with pytest.raises(ValidationError):
        CreateCavityQuality(
            cavity_id=1, inspected_quantity=10, defect_quantity=0, result='FAIL'
        )
