from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from orm_models.customer import Customer
from orm_models.customer_mailbox import CustomerMailbox
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement
from orm_models.mailbox import Mailbox
from orm_models.streaming_service import StreamingService


class CustomerStreamingEntitlementRepository(Protocol):
    async def upsert(
        self,
        *,
        entity_id: int,
        customer_id: int,
        streaming_service_id: int,
        mailbox_id: int,
        status: str,
    ) -> CustomerStreamingEntitlement: ...


class DbCustomerStreamingEntitlementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _assert_customer(self, entity_id: int, customer_id: int) -> Customer:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.entity_id == entity_id,
            Customer.deleted_at.is_(None),
        )
        c = (await self._db.execute(stmt)).scalars().first()
        if not c:
            raise NotFoundError("Customer not found")
        return c

    async def _assert_streaming_service(self, streaming_service_id: int) -> None:
        stmt = select(StreamingService.id).where(
            StreamingService.id == streaming_service_id,
            StreamingService.deleted_at.is_(None),
        )
        if not (await self._db.execute(stmt)).scalar():
            raise NotFoundError("Streaming service not found")

    async def _assert_mailbox(self, entity_id: int, mailbox_id: int) -> Mailbox:
        stmt = select(Mailbox).where(
            Mailbox.id == mailbox_id,
            Mailbox.entity_id == entity_id,
            Mailbox.deleted_at.is_(None),
        )
        m = (await self._db.execute(stmt)).scalars().first()
        if not m:
            raise NotFoundError("Mailbox not found")
        return m

    async def _assert_customer_mailbox(
        self, customer_id: int, mailbox_id: int
    ) -> None:
        stmt = select(CustomerMailbox.id).where(
            CustomerMailbox.customer_id == customer_id,
            CustomerMailbox.mailbox_id == mailbox_id,
            CustomerMailbox.deleted_at.is_(None),
        )
        if not (await self._db.execute(stmt)).first():
            raise ConflictError("Customer is not linked to this mailbox; link them first")

    async def upsert(
        self,
        *,
        entity_id: int,
        customer_id: int,
        streaming_service_id: int,
        mailbox_id: int,
        status: str,
    ) -> CustomerStreamingEntitlement:
        await self._assert_customer(entity_id, customer_id)
        await self._assert_streaming_service(streaming_service_id)
        await self._assert_mailbox(entity_id, mailbox_id)
        await self._assert_customer_mailbox(customer_id, mailbox_id)

        stmt = select(CustomerStreamingEntitlement).where(
            CustomerStreamingEntitlement.customer_id == customer_id,
            CustomerStreamingEntitlement.streaming_service_id == streaming_service_id,
            CustomerStreamingEntitlement.deleted_at.is_(None),
        )
        row = (await self._db.execute(stmt)).scalars().first()
        if row is None:
            row = CustomerStreamingEntitlement(
                customer_id=customer_id,
                streaming_service_id=streaming_service_id,
                mailbox_id=mailbox_id,
                status=status,
            )
            self._db.add(row)
        else:
            row.mailbox_id = mailbox_id
            row.status = status
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Entitlement could not be saved") from e
        await self._db.refresh(row)
        return row

    async def soft_delete(
        self, *, entity_id: int, customer_id: int, streaming_service_id: int
    ) -> None:
        await self._assert_customer(entity_id, customer_id)
        stmt = select(CustomerStreamingEntitlement).where(
            CustomerStreamingEntitlement.customer_id == customer_id,
            CustomerStreamingEntitlement.streaming_service_id == streaming_service_id,
            CustomerStreamingEntitlement.deleted_at.is_(None),
        )
        row = (await self._db.execute(stmt)).scalars().first()
        if not row:
            raise NotFoundError("Entitlement not found")
        row.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()
