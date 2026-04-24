from __future__ import annotations

from collections.abc import Sequence

from api.repositories.streaming_services import StreamingServiceRepository
from orm_models.streaming_service import StreamingService


class StreamingServicesService:
    def __init__(self, repo: StreamingServiceRepository) -> None:
        self._repo = repo

    async def create(self, *, slug: str, display_name: str, keyword_patterns: list[str] | None) -> StreamingService:
        return await self._repo.create(slug=slug, display_name=display_name, keyword_patterns=keyword_patterns)

    async def get(self, *, service_id: int) -> StreamingService:
        return await self._repo.get(service_id=service_id)

    async def list(self, *, limit: int, offset: int) -> Sequence[StreamingService]:
        return await self._repo.list(limit=limit, offset=offset)

    async def update(
        self, *, service_id: int, display_name: str | None, keyword_patterns: list[str] | None
    ) -> StreamingService:
        return await self._repo.update(service_id=service_id, display_name=display_name, keyword_patterns=keyword_patterns)

    async def soft_delete(self, *, service_id: int) -> None:
        await self._repo.soft_delete(service_id=service_id)

