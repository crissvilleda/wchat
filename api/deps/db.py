from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_async_sessionmaker


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

