from backend.plugin.equipment.api.v1.mes.equipment import router


def test_equipment_router_exposes_the_master_data_contract() -> None:
    endpoints = {(route.path, frozenset(route.methods or set())) for route in router.routes}

    assert ('', frozenset({'GET'})) in endpoints
    assert ('', frozenset({'POST'})) in endpoints
    assert ('/{equipment_id}', frozenset({'GET'})) in endpoints
    assert ('/{equipment_id}', frozenset({'PUT'})) in endpoints
    assert ('/{equipment_id}/enabled', frozenset({'PUT'})) in endpoints
    assert ('/{equipment_id}/status', frozenset({'PUT'})) in endpoints
    assert ('/options', frozenset({'GET'})) in endpoints
    assert ('/category/tree', frozenset({'GET'})) in endpoints
    assert ('/category', frozenset({'POST'})) in endpoints
    assert ('/category/{category_id}', frozenset({'PUT'})) in endpoints
