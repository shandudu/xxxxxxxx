"""Validate ORM rows survive pagination before service-layer enrichment."""
from __future__ import annotations

import asyncio

from fastapi_pagination.api import _req_val, set_page, set_params
from starlette.requests import Request

from backend.common.pagination import _CustomPage, _CustomPageParams
from backend.database.db import async_db_session
from backend.plugin.bom.service.bom_service import bom_service
from backend.plugin.customer.service.customer_service import customer_service
from backend.plugin.material.service.material_service import material_service
from backend.plugin.routing.service.routing_service import routing_service
from backend.plugin.supplier.service.supplier_service import supplier_service


async def validate() -> None:
    request = Request({
        'type': 'http', 'http_version': '1.1', 'method': 'GET',
        'scheme': 'http', 'path': '/validation', 'raw_path': b'/validation',
        'query_string': b'page=1&size=100', 'headers': [],
        'client': ('127.0.0.1', 1), 'server': ('127.0.0.1', 8000),
        'root_path': '',
    })
    request_token = _req_val.set(request)
    try:
        with set_page(_CustomPage), set_params(_CustomPageParams(page=1, size=100)):
            async with async_db_session() as db:
                customers = await customer_service.list_customers(
                    db, None, None, None, None, None, None, None, None, None, None,
                )
                boms = await bom_service.list_boms(db, None, None, 14, None, None, None)
                materials = await material_service.list_materials(
                    db, None, None, None, None, None, None, None, None,
                )
                suppliers = await supplier_service.list_suppliers(
                    db, None, None, None, None, None, None,
                )
                routings = await routing_service.list_routings(
                    db, None, None, None, None, None, None,
                )
                print(
                    'PAGINATION_ORM_MYSQL_OK '
                    f'customers={len(customers["items"])} '
                    f'boms_product_14={len(boms["items"])} '
                    f'materials={len(materials["items"])} '
                    f'suppliers={len(suppliers["items"])} '
                    f'routings={len(routings["items"])}'
                )
    finally:
        _req_val.reset(request_token)


if __name__ == '__main__':
    asyncio.run(validate())
