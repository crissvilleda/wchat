from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from orm_models.streaming_account import StreamingAccount
from orm_models.streaming_service import StreamingService


class StreamingAccountRepository(Protocol):
    async def create(
        self, *, entity_id: int, streaming_service_id: int, label: str, is_active: bool
    ) -> StreamingAccount: ...
    async def get(self, *, entity_id: int, streaming_account_id: int) -> StreamingAccount: ...
    async def list(self, *, entity_id: int, limit: int, offset: int) -> Sequence[StreamingAccount]: ...
    async def update(
        self,
        *,
        entity_id: int,
        streaming_account_id: int,
        streaming_service_id: int | None,
        label: str | None,
        is_active: bool | None,
    ) -> StreamingAccount: ...
    async def soft_delete(self, *, entity_id: int, streaming_account_id: int) -> None: ...


class DbStreamingAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _ensure_service_exists(self, streaming_service_id: int) -> None:
        stmt = select(StreamingService.id).where(
            StreamingService.id == streaming_service_id,
            StreamingService.deleted_at.is_(None),
        )
        exists = (await self._db.execute(stmt)).scalar_one_or_none()
        if not exists:
            raise NotFoundError("Streaming service not found")

    async def create(
        self, *, entity_id: int, streaming_service_id: int, label: str, is_active: bool
    ) -> StreamingAccount:
        await self._ensure_service_exists(streaming_service_id)
        acc = StreamingAccount(
            entity_id=entity_id,
            streaming_service_id=streaming_service_id,
            label=label,
            is_active=is_active,
        )
        self._db.add(acc)
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Streaming account already exists") from e
        await self._db.refresh(acc)
        return acc

    async def get(self, *, entity_id: int, streaming_account_id: int) -> StreamingAccount:
        stmt = select(StreamingAccount).where(
            StreamingAccount.id == streaming_account_id,
            StreamingAccount.entity_id == entity_id,
            StreamingAccount.deleted_at.is_(None),
        )
        acc = (await self._db.execute(stmt)).scalars().first()
        if not acc:
            raise NotFoundError("Streaming account not found")
        return acc

    async def list(self, *, entity_id: int, limit: int, offset: int) -> Sequence[StreamingAccount]:
        stmt = (
            select(StreamingAccount)
            .where(StreamingAccount.entity_id == entity_id, StreamingAccount.deleted_at.is_(None))
            .order_by(StreamingAccount.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def update(
        self,
        *,
        entity_id: int,
        streaming_account_id: int,
        streaming_service_id: int | None,
        label: str | None,
        is_active: bool | None,
    ) -> StreamingAccount:
        acc = await self.get(entity_id=entity_id, streaming_account_id=streaming_account_id)
        if streaming_service_id is not None:
            await self._ensure_service_exists(streaming_service_id)
            acc.streaming_service_id = streaming_service_id
        if label is not None:
            acc.label = label
        if is_active is not None:
            acc.is_active = is_active
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Update conflict") from e
        await self._db.refresh(acc)
        return acc

    async def soft_delete(self, *, entity_id: int, streaming_account_id: int) -> None:
        acc = await self.get(entity_id=entity_id, streaming_account_id=streaming_account_id)
        acc.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()

