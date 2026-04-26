from __future__ import annotations

from collections.abc import Sequence

from api.pagination.cursor import encode_id_cursor
from api.repositories.streaming_services import StreamingServiceRepository
from orm_models.streaming_service import StreamingService


class StreamingServicesService:
    def __init__(self, repo: StreamingServiceRepository) -> None:
        self._repo = repo

    async def get(self, *, service_id: int) -> StreamingService:
        return await self._repo.get(service_id=service_id)

    async def list(
        self, *, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[StreamingService], str | None]:
        rows, next_id = await self._repo.list(limit=limit, after_id=after_id, q=q)
        if next_id is not None:
            return rows, encode_id_cursor(next_id)
        return rows, None
