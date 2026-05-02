from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from uuid import uuid4

# asyncpg
from asyncpg import Connection


class CustomConnection(Connection):
    def _get_unique_id(self, prefix: str) -> str:
        return f'__asyncpg_{prefix}_{uuid4()}__'
        

def _get_db_url_async() -> str:
    url = os.getenv("DB_URL_ASYNC")
    if not url:
        raise RuntimeError("DB_URL_ASYNC env var is required")
    return url


@lru_cache
def get_async_engine() -> AsyncEngine:
    url = _get_db_url_async()
    if url.startswith("postgresql"):
        connect_args: dict = {"server_settings": {"search_path": "private,public"}}
    else:
        connect_args = {}
    return create_async_engine(
        url,
        pool_pre_ping=True,
        poolclass=NullPool,
        connect_args={
            **connect_args,
            "statement_cache_size": 0,
            "connection_class": CustomConnection,
        },
    )


@lru_cache
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

