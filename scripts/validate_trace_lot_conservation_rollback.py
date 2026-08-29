"""Validate lot split/merge quantity conservation in MySQL and roll back."""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import SALES_ORDER_DRIVEN_REFERENCES, demo_service
from backend.plugin.trace.enums import LotStatus
from backend.plugin.trace.model import MaterialLot
from backend.plugin.trace.schema.trace import LotMergeParam, LotSplitParam
from backend.plugin.trace.service.trace_service import trace_service


class _RollbackValidation(Exception):
    pass


async def validate() -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                source = await db.scalar(
                    select(MaterialLot).where(
                        MaterialLot.lot_no == SALES_ORDER_DRIVEN_REFERENCES['finished_lot'],
                        MaterialLot.deleted == 0,
                    )
                )
                if not source or source.quantity is None or source.quantity <= 0:
                    raise RuntimeError('trace source lot missing')
                first = (source.quantity / Decimal('2')).quantize(Decimal('0.000001'))
                second = source.quantity - first
                children = await trace_service.split_lot(
                    db,
                    source.id,
                    LotSplitParam(
                        children=[
                            {'lot_no': 'TRACE-CONSERVE-SPLIT-01', 'quantity': first},
                            {'lot_no': 'TRACE-CONSERVE-SPLIT-02', 'quantity': second},
                        ]
                    ),
                )
                if source.status != LotStatus.CLOSED:
                    raise RuntimeError('fully split source lot was not closed')
                try:
                    await trace_service.split_lot(
                        db,
                        source.id,
                        LotSplitParam(
                            children=[{'lot_no': 'TRACE-CONSERVE-OVERFLOW', 'quantity': Decimal('1')}]
                        ),
                    )
                except errors.ConflictError:
                    pass
                else:
                    raise RuntimeError('closed source lot was split repeatedly')
                source_ids = [int(item['id']) for item in children]
                try:
                    await trace_service.merge_lots(
                        db,
                        LotMergeParam(
                            source_lot_ids=source_ids,
                            target_lot={
                                'material_id': source.material_id,
                                'lot_no': 'TRACE-CONSERVE-MERGE-BAD',
                                'quantity': source.quantity + Decimal('1'),
                                'unit_id': source.unit_id,
                            },
                        ),
                    )
                except errors.ConflictError as exc:
                    if exc.msg != 'LOT_MERGE_QUANTITY_MISMATCH':
                        raise
                else:
                    raise RuntimeError('non-conserving lot merge was accepted')
                merged = await trace_service.merge_lots(
                    db,
                    LotMergeParam(
                        source_lot_ids=source_ids,
                        target_lot={
                            'material_id': source.material_id,
                            'lot_no': 'TRACE-CONSERVE-MERGED',
                            'unit_id': source.unit_id,
                        },
                    ),
                )
                if Decimal(merged['quantity']) != source.quantity:
                    raise RuntimeError('merged lot quantity does not equal source quantity')
                print(f"TRACE_LOT_CONSERVATION_RUN_OK quantity={merged['quantity']}")
                raise _RollbackValidation
        except _RollbackValidation:
            print('TRACE_LOT_CONSERVATION_ROLLBACK_OK')


if __name__ == '__main__':
    asyncio.run(validate())
