from __future__ import annotations

from api.repositories.customer_streaming_entitlements import (
    CustomerStreamingEntitlementRepository,
)
from api.schemas.customer_streaming_entitlement_overview import (
    CustomerStreamingAssignmentOut,
    EntitlementLinkOut,
    MailboxLinkOut,
)
from api.schemas.streaming_service import StreamingServiceOut
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

    async def list_assignments_for_customer(
        self, *, entity_id: int, customer_id: int
    ) -> list[CustomerStreamingAssignmentOut]:
        pairs = await self._repo.list_assignments_for_customer(
            entity_id=entity_id, customer_id=customer_id
        )
        out: list[CustomerStreamingAssignmentOut] = []
        for svc, ent in pairs:
            mailbox_out: MailboxLinkOut | None = None
            entitlement_out: EntitlementLinkOut | None = None
            if ent is not None:
                entitlement_out = EntitlementLinkOut(id=ent.id, status=ent.status)
                mb = ent.mailbox
                if (
                    mb is not None
                    and mb.deleted_at is None
                    and mb.entity_id == entity_id
                ):
                    mailbox_out = MailboxLinkOut(
                        id=mb.id,
                        provider=mb.provider,
                        mailbox_address=mb.mailbox_address,
                    )
            out.append(
                CustomerStreamingAssignmentOut(
                    streaming_service=StreamingServiceOut.model_validate(svc),
                    entitlement=entitlement_out,
                    mailbox=mailbox_out,
                )
            )
        return out
