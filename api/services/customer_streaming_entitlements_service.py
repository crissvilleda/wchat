from __future__ import annotations

from api.repositories.customer_streaming_entitlements import (
    CustomerStreamingEntitlementRepository,
)
from api.repositories.mailboxes import MailboxRepository
from api.schemas.customer_streaming_entitlement_overview import (
    CustomerStreamingAssignmentOut,
    EntitlementLinkOut,
    MailboxLinkOut,
)
from api.schemas.customer_streaming_entitlements_sync import (
    CustomerStreamingEntitlementAssignmentIn,
)
from api.schemas.streaming_service import StreamingServiceOut
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement


class CustomerStreamingEntitlementsService:
    def __init__(
        self,
        repo: CustomerStreamingEntitlementRepository,
        mailbox_repo: MailboxRepository,
    ) -> None:
        self._repo = repo
        self._mailbox_repo = mailbox_repo

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

    async def sync_assignments(
        self,
        *,
        entity_id: int,
        customer_id: int,
        assignments: list[CustomerStreamingEntitlementAssignmentIn],
    ) -> list[CustomerStreamingAssignmentOut]:
        keep = {a.streaming_service_id for a in assignments}
        await self._repo.soft_delete_entitlements_not_in(
            entity_id=entity_id,
            customer_id=customer_id,
            keep_streaming_service_ids=keep,
        )
        for a in assignments:
            await self._mailbox_repo.ensure_customer_mailbox_link(
                entity_id=entity_id,
                mailbox_id=a.mailbox_id,
                customer_id=customer_id,
            )
            await self._repo.upsert(
                entity_id=entity_id,
                customer_id=customer_id,
                streaming_service_id=a.streaming_service_id,
                mailbox_id=a.mailbox_id,
                status=a.status,
            )
        await self._mailbox_repo.prune_orphan_customer_mailbox_links(
            entity_id=entity_id,
            customer_id=customer_id,
        )
        return await self.list_assignments_for_customer(
            entity_id=entity_id, customer_id=customer_id
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
