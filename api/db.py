from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _get_db_url_async() -> str:
    url = os.getenv("DB_URL_ASYNC")
    if not url:
        raise RuntimeError("DB_URL_ASYNC env var is required")
    return url


@lru_cache
def get_async_engine() -> AsyncEngine:
    return create_async_engine(_get_db_url_async(), pool_pre_ping=True)


@lru_cache
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

