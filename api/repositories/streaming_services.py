from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import String, cast, select

from api.repositories.search import ilike_or_columns, keyset_paginate_result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from orm_models.streaming_service import StreamingService


class StreamingServiceRepository(Protocol):
    async def create(self, *, slug: str, display_name: str, keyword_patterns: list[str] | None) -> StreamingService: ...
    async def get(self, *, service_id: int) -> StreamingService: ...
    async def list(
        self, *, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[StreamingService], int | None]: ...
    async def update(
        self, *, service_id: int, display_name: str | None, keyword_patterns: list[str] | None
    ) -> StreamingService: ...
    async def soft_delete(self, *, service_id: int) -> None: ...


class DbStreamingServiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, slug: str, display_name: str, keyword_patterns: list[str] | None) -> StreamingService:
        service = StreamingService(slug=slug, display_name=display_name, keyword_patterns=keyword_patterns)
        self._db.add(service)
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Streaming service already exists") from e
        await self._db.refresh(service)
        return service

    async def get(self, *, service_id: int) -> StreamingService:
        stmt = select(StreamingService).where(StreamingService.id == service_id, StreamingService.deleted_at.is_(None))
        service = (await self._db.execute(stmt)).scalars().first()
        if not service:
            raise NotFoundError("Streaming service not found")
        return service

    async def list(
        self, *, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[StreamingService], int | None]:
        stmt = select(StreamingService).where(StreamingService.deleted_at.is_(None))
        if after_id is not None:
            stmt = stmt.where(StreamingService.id > after_id)
        if q is not None:
            kw_as_text = cast(StreamingService.keyword_patterns, String)
            stmt = stmt.where(
                ilike_or_columns(StreamingService.slug, StreamingService.display_name, kw_as_text, term=q)
            )
        stmt = stmt.order_by(StreamingService.id.asc()).limit(limit + 1)
        rows = (await self._db.execute(stmt)).scalars().all()
        page, next_id = keyset_paginate_result(rows, limit=limit, id_getter="id")
        return page, next_id

    async def update(
        self, *, service_id: int, display_name: str | None, keyword_patterns: list[str] | None
    ) -> StreamingService:
        service = await self.get(service_id=service_id)
        if display_name is not None:
            service.display_name = display_name
        # keyword_patterns is intentionally nullable; allow explicit None to clear.
        service.keyword_patterns = keyword_patterns
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Update conflict") from e
        await self._db.refresh(service)
        return service

    async def soft_delete(self, *, service_id: int) -> None:
        service = await self.get(service_id=service_id)
        service.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()

