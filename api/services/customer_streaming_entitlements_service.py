from __future__ import annotations

from api.repositories.customer_streaming_entitlements import (
    CustomerStreamingEntitlementRepository,
)
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement


class CustomerStreamingEntitlementsService:
    def __init__(self, repo: CustomerStreamingEntitlementRepository) -> None:
        self._repo = repo

    async def upsert(
        self,
        *,
        entity_id: int,
        customer_id: int,
        streaming_service_id: int,
        mailbox_id: int,
        status: str,
    ) -> CustomerStreamingEntitlement:
        return await self._repo.upsert(
            entity_id=entity_id,
            customer_id=customer_id,
            streaming_service_id=streaming_service_id,
            mailbox_id=mailbox_id,
            status=status,
        )

    async def soft_delete(
        self, *, entity_id: int, customer_id: int, streaming_service_id: int
    ) -> None:
        await self._repo.soft_delete(
            entity_id=entity_id,
            customer_id=customer_id,
            streaming_service_id=streaming_service_id,
        )
