from __future__ import annotations

from collections.abc import Sequence

from api.pagination.cursor import encode_id_cursor
from api.repositories.customers import CustomerRepository
from orm_models.customer import Customer


class CustomersService:
    def __init__(self, repo: CustomerRepository) -> None:
        self._repo = repo

    async def create(self, *, entity_id: int, name: str, whatsapp_e164: str) -> Customer:
        return await self._repo.create(entity_id=entity_id, name=name, whatsapp_e164=whatsapp_e164)

    async def get(self, *, entity_id: int, customer_id: int) -> Customer:
        return await self._repo.get(entity_id=entity_id, customer_id=customer_id)

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Customer], str | None]:
        rows, next_id = await self._repo.list(
            entity_id=entity_id, limit=limit, after_id=after_id, q=q
        )
        if next_id is not None:
            return rows, encode_id_cursor(next_id)
        return rows, None

    async def update(
        self, *, entity_id: int, customer_id: int, name: str | None, whatsapp_e164: str | None
    ) -> Customer:
        return await self._repo.update(
            entity_id=entity_id,
            customer_id=customer_id,
            name=name,
            whatsapp_e164=whatsapp_e164,
        )

    async def soft_delete(self, *, entity_id: int, customer_id: int) -> None:
        await self._repo.soft_delete(entity_id=entity_id, customer_id=customer_id)

