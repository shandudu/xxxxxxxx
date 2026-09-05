"""Validate bilingual dictionary schema and locale values against MySQL."""
from __future__ import annotations

import asyncio

from sqlalchemy import inspect, text

from backend.database.db import async_db_session, async_engine


async def main() -> None:
    async with async_engine.connect() as connection:
        columns = await connection.run_sync(
            lambda sync_connection: {column['name'] for column in inspect(sync_connection).get_columns('sys_dict_data')}
        )
    async with async_db_session() as db:
        total = int(await db.scalar(text('SELECT COUNT(*) FROM sys_dict_data WHERE deleted = 0')) or 0)
        key_labels = int(await db.scalar(text('SELECT COUNT(*) FROM sys_dict_data WHERE deleted = 0 AND label = value')) or 0)
        print(f'dictionary_rows={total} labels_equal_keys={key_labels}')
        required = {'label_zh_cn', 'label_en_us'}
        if not required.issubset(columns):
            print('INFO: bilingual columns are not installed at the current migration revision')
        else:
            missing_zh = int(await db.scalar(text("SELECT COUNT(*) FROM sys_dict_data WHERE deleted = 0 AND (label_zh_cn IS NULL OR label_zh_cn = '')")) or 0)
            configured_en = int(await db.scalar(text("SELECT COUNT(*) FROM sys_dict_data WHERE deleted = 0 AND label_en_us IS NOT NULL AND label_en_us != ''")) or 0)
            if missing_zh:
                raise RuntimeError(f'{missing_zh} active dictionary rows have no Chinese value')
            print(f'OK: bilingual dictionary columns, Chinese fallback values, english_configured={configured_en}')
    await async_engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
