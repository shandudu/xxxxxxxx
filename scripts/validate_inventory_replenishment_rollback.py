"""Validate safety-stock replenishment calculation and release."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.inventory.enums import ReplenishmentAlertLevel, ReplenishmentStatus
from backend.plugin.inventory.schema.inventory import GenerateReplenishment, InventoryPolicyUpsert, ReleaseReplenishment
from backend.plugin.inventory.service import replenishment_service
from backend.plugin.material.model import Material
from backend.plugin.supplier.model import Supplier


class _RollbackValidation(Exception):
    pass


async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                material = await db.scalar(
                    select(Material).where(
                        Material.material_code == 'DEMO-SOD-RM-001',
                        Material.deleted == 0,
                    )
                )
                supplier = await db.scalar(
                    select(Supplier).where(Supplier.deleted == 0).order_by(Supplier.id.desc())
                )
                if not material or not supplier:
                    raise RuntimeError('demo replenishment master data missing')
                await replenishment_service.upsert_policy(
                    db,
                    material.id,
                    InventoryPolicyUpsert(
                        safety_stock=Decimal('20'),
                        reorder_point=Decimal('40'),
                        max_stock=Decimal('100'),
                        min_order_quantity=Decimal('10'),
                    ),
                )
                suggestions = await replenishment_service.generate(
                    db, GenerateReplenishment(material_ids=[material.id])
                )
                if not suggestions or suggestions[0].alert_level == ReplenishmentAlertLevel.COVERED:
                    raise RuntimeError('replenishment suggestion missing')
                firmed = await replenishment_service.firm(db, suggestions[0].id)
                released = await replenishment_service.release(
                    db,
                    firmed.id,
                    ReleaseReplenishment(supplier_id=supplier.id),
                )
                if released.status != ReplenishmentStatus.RELEASED:
                    raise RuntimeError('replenishment release failed')
                print(
                    f'INVENTORY_REPLENISHMENT_RUN_OK material={material.material_code} '
                    f'alert={released.alert_level} quantity={released.suggested_quantity} '
                    f'document={released.source_document_no}'
                )
                if not commit:
                    raise _RollbackValidation
        except _RollbackValidation:
            print('INVENTORY_REPLENISHMENT_ROLLBACK_OK')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    asyncio.run(validate(parser.parse_args().commit))


if __name__ == '__main__':
    main()
