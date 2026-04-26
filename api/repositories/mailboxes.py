from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.search import ilike_or_columns, keyset_paginate_result
from orm_models.customer import Customer
from orm_models.customer_mailbox import CustomerMailbox
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement
from orm_models.mailbox import Mailbox


class MailboxRepository(Protocol):
    async def create(
        self,
        *,
        entity_id: int,
        provider: str,
        mailbox_address: str,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry: datetime | None,
        max_customer_links: int | None,
    ) -> Mailbox: ...

    async def get(self, *, entity_id: int, mailbox_id: int) -> Mailbox: ...

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Mailbox], int | None]: ...

    async def update(
        self,
        *,
        entity_id: int,
        mailbox_id: int,
        provider: str | None,
        mailbox_address: str | None,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry: datetime | None,
        revoked_at: datetime | None,
        max_customer_links: int | None,
    ) -> Mailbox: ...

    async def soft_delete(self, *, entity_id: int, mailbox_id: int) -> None: ...

    async def count_customer_links(self, *, mailbox_id: int) -> int: ...

    async def link_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int) -> CustomerMailbox: ...

    async def unlink_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int) -> None: ...


class DbMailboxRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _count_active_links(self, mailbox_id: int) -> int:
        stmt = select(func.count()).select_from(CustomerMailbox).where(
            CustomerMailbox.mailbox_id == mailbox_id,
            CustomerMailbox.deleted_at.is_(None),
        )
        return int((await self._db.execute(stmt)).scalar() or 0)

    async def create(
        self,
        *,
        entity_id: int,
        provider: str,
        mailbox_address: str,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry: datetime | None,
        max_customer_links: int | None,
    ) -> Mailbox:
        row = Mailbox(
            entity_id=entity_id,
            provider=provider,
            mailbox_address=mailbox_address,
            credential_payload=credential_payload,
            secret_ref=secret_ref,
            token_scopes=token_scopes,
            token_expiry=token_expiry,
            max_customer_links=max_customer_links,
        )
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Mailbox already exists for this address") from e
        await self._db.refresh(row)
        return row

    async def get(self, *, entity_id: int, mailbox_id: int) -> Mailbox:
        stmt = select(Mailbox).where(
            Mailbox.id == mailbox_id,
            Mailbox.entity_id == entity_id,
            Mailbox.deleted_at.is_(None),
        )
        row = (await self._db.execute(stmt)).scalars().first()
        if not row:
            raise NotFoundError("Mailbox not found")
        return row

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Mailbox], int | None]:
        stmt = select(Mailbox).where(
            Mailbox.entity_id == entity_id,
            Mailbox.deleted_at.is_(None),
        )
        if after_id is not None:
            stmt = stmt.where(Mailbox.id > after_id)
        if q is not None:
            stmt = stmt.where(
                ilike_or_columns(Mailbox.mailbox_address, Mailbox.provider, term=q)
            )
        stmt = stmt.order_by(Mailbox.id.asc()).limit(limit + 1)
        rows = (await self._db.execute(stmt)).scalars().all()
        page, next_id = keyset_paginate_result(rows, limit=limit, id_getter="id")
        return page, next_id

    async def update(
        self,
        *,
        entity_id: int,
        mailbox_id: int,
        provider: str | None,
        mailbox_address: str | None,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry: datetime | None,
        revoked_at: datetime | None,
        max_customer_links: int | None,
    ) -> Mailbox:
        row = await self.get(entity_id=entity_id, mailbox_id=mailbox_id)
        if provider is not None:
            row.provider = provider
        if mailbox_address is not None:
            row.mailbox_address = mailbox_address
        if credential_payload is not None:
            row.credential_payload = credential_payload
        if secret_ref is not None:
            row.secret_ref = secret_ref
        if token_scopes is not None:
            row.token_scopes = token_scopes
        if token_expiry is not None:
            row.token_expiry = token_expiry
        if revoked_at is not None:
            row.revoked_at = revoked_at
        if max_customer_links is not None:
            row.max_customer_links = max_customer_links
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Update conflict") from e
        await self._db.refresh(row)
        return row

    async def soft_delete(self, *, entity_id: int, mailbox_id: int) -> None:
        row = await self.get(entity_id=entity_id, mailbox_id=mailbox_id)
        row.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()

    async def count_customer_links(self, *, mailbox_id: int) -> int:
        return await self._count_active_links(mailbox_id)

    async def _get_customer_in_entity(self, entity_id: int, customer_id: int) -> Customer:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.entity_id == entity_id,
            Customer.deleted_at.is_(None),
        )
        c = (await self._db.execute(stmt)).scalars().first()
        if not c:
            raise NotFoundError("Customer not found")
        return c

    async def link_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int) -> CustomerMailbox:
        m = await self.get(entity_id=entity_id, mailbox_id=mailbox_id)
        await self._get_customer_in_entity(entity_id, customer_id)
        n = await self._count_active_links(m.id)
        if m.max_customer_links is not None and n >= m.max_customer_links:
            raise ConflictError("Mailbox has reached max customer links")
        link = CustomerMailbox(customer_id=customer_id, mailbox_id=mailbox_id)
        self._db.add(link)
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Customer is already linked to this mailbox") from e
        await self._db.refresh(link)
        return link

    async def unlink_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int) -> None:
        await self.get(entity_id=entity_id, mailbox_id=mailbox_id)
        ent_stmt = select(CustomerStreamingEntitlement.id).where(
            CustomerStreamingEntitlement.customer_id == customer_id,
            CustomerStreamingEntitlement.mailbox_id == mailbox_id,
            CustomerStreamingEntitlement.deleted_at.is_(None),
        )
        if (await self._db.execute(ent_stmt)).first():
            raise ConflictError(
                "Reassign or remove entitlements that use this customer/mailbox pair first"
            )
        link_stmt = select(CustomerMailbox).where(
            CustomerMailbox.customer_id == customer_id,
            CustomerMailbox.mailbox_id == mailbox_id,
            CustomerMailbox.deleted_at.is_(None),
        )
        link = (await self._db.execute(link_stmt)).scalars().first()
        if not link:
            raise NotFoundError("Customer is not linked to this mailbox")
        link.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()
