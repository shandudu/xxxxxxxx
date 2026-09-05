"""Validate phase-two configurable UI messages against MySQL."""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from backend.database.db import async_db_session, async_engine


async def main() -> None:
    async with async_db_session() as db:
        type_count = int(await db.scalar(text(
            "SELECT COUNT(*) FROM sys_dict_type "
            "WHERE code IN ('ui_tips', 'api_errors') AND deleted = 0"
        )) or 0)
        message_count = int(await db.scalar(text(
            "SELECT COUNT(*) FROM sys_dict_data "
            "WHERE type_code IN ('ui_tips', 'api_errors') AND deleted = 0"
        )) or 0)
        missing_locale = int(await db.scalar(text(
            "SELECT COUNT(*) FROM sys_dict_data "
            "WHERE type_code IN ('ui_tips', 'api_errors') AND deleted = 0 "
            "AND (label_zh_cn IS NULL OR label_zh_cn = '' OR label_en_us IS NULL OR label_en_us = '')"
        )) or 0)
        duplicate_keys = int(await db.scalar(text(
            "SELECT COUNT(*) FROM ("
            "SELECT type_code, value FROM sys_dict_data "
            "WHERE type_code IN ('ui_tips', 'api_errors') AND deleted = 0 "
            "GROUP BY type_code, value HAVING COUNT(*) > 1"
            ") duplicated"
        )) or 0)
        if type_count != 2:
            raise RuntimeError(f'expected 2 configurable message dictionary types, got {type_count}')
        if message_count < 70:
            raise RuntimeError(f'expected at least 70 configurable messages, got {message_count}')
        if missing_locale or duplicate_keys:
            raise RuntimeError(
                f'invalid configurable messages: missing_locale={missing_locale}, duplicate_keys={duplicate_keys}'
            )
        print(f'OK: dictionary_types={type_count}, messages={message_count}, bilingual={message_count}')
    await async_engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
