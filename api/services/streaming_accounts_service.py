from __future__ import annotations

from collections.abc import Sequence

from api.pagination.cursor import encode_id_cursor
from api.repositories.streaming_accounts import StreamingAccountRepository
from orm_models.streaming_account import StreamingAccount


class StreamingAccountsService:
    def __init__(self, repo: StreamingAccountRepository) -> None:
        self._repo = repo

    async def create(
        self, *, entity_id: int, streaming_service_id: int, label: str, is_active: bool
    ) -> StreamingAccount:
        return await self._repo.create(
            entity_id=entity_id,
            streaming_service_id=streaming_service_id,
            label=label,
            is_active=is_active,
        )

    async def get(self, *, entity_id: int, streaming_account_id: int) -> StreamingAccount:
        return await self._repo.get(entity_id=entity_id, streaming_account_id=streaming_account_id)

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[StreamingAccount], str | None]:
        rows, next_id = await self._repo.list(
            entity_id=entity_id, limit=limit, after_id=after_id, q=q
        )
        if next_id is not None:
            return rows, encode_id_cursor(next_id)
        return rows, None

    async def update(
        self,
        *,
        entity_id: int,
        streaming_account_id: int,
        streaming_service_id: int | None,
        label: str | None,
        is_active: bool | None,
    ) -> StreamingAccount:
        return await self._repo.update(
            entity_id=entity_id,
            streaming_account_id=streaming_account_id,
            streaming_service_id=streaming_service_id,
            label=label,
            is_active=is_active,
        )

    async def soft_delete(self, *, entity_id: int, streaming_account_id: int) -> None:
        await self._repo.soft_delete(entity_id=entity_id, streaming_account_id=streaming_account_id)

