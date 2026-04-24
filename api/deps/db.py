from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.db import get_async_sessionmaker


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return get_async_sessionmaker()
