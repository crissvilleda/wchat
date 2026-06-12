from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from api.pagination.cursor import encode_id_cursor
from api.repositories.mailboxes import MailboxRepository
from orm_models.mailbox import Mailbox


class MailboxesService:
    def __init__(self, repo: MailboxRepository) -> None:
        self._repo = repo

    async def create(
        self,
        *,
        entity_id: int,
        provider: str,
        mailbox_address: str,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry,
        max_customer_links: int | None,
    ) -> Mailbox:
        return await self._repo.create(
            entity_id=entity_id,
            provider=provider,
            mailbox_address=mailbox_address,
            credential_payload=credential_payload,
            secret_ref=secret_ref,
            token_scopes=token_scopes,
            token_expiry=token_expiry,
            max_customer_links=max_customer_links,
        )

    async def get(self, *, entity_id: int, mailbox_id: int) -> Mailbox:
        return await self._repo.get(entity_id=entity_id, mailbox_id=mailbox_id)

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Mailbox], str | None]:
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
        mailbox_id: int,
        provider: str | None,
        mailbox_address: str | None,
        credential_payload: dict | None,
        secret_ref: str | None,
        token_scopes: str | None,
        token_expiry,
        revoked_at,
        max_customer_links: int | None,
    ) -> Mailbox:
        return await self._repo.update(
            entity_id=entity_id,
            mailbox_id=mailbox_id,
            provider=provider,
            mailbox_address=mailbox_address,
            credential_payload=credential_payload,
            secret_ref=secret_ref,
            token_scopes=token_scopes,
            token_expiry=token_expiry,
            revoked_at=revoked_at,
            max_customer_links=max_customer_links,
        )

    async def upsert_gmail_credentials(
        self,
        *,
        entity_id: int,
        mailbox_address: str,
        credential_payload: dict,
        token_scopes: str | None,
        token_expiry: datetime | None,
    ) -> Mailbox:
        existing = await self._repo.get_by_entity_and_address(
            entity_id=entity_id, mailbox_address=mailbox_address
        )
        if existing is not None:
            return await self._repo.update_credentials(
                entity_id=entity_id,
                mailbox_id=existing.id,
                credential_payload=credential_payload,
                token_scopes=token_scopes,
                token_expiry=token_expiry,
            )
        return await self._repo.create(
            entity_id=entity_id,
            provider="gmail",
            mailbox_address=mailbox_address,
            credential_payload=credential_payload,
            secret_ref=None,
            token_scopes=token_scopes,
            token_expiry=token_expiry,
            max_customer_links=None,
        )

    async def soft_delete(self, *, entity_id: int, mailbox_id: int) -> None:
        await self._repo.soft_delete(entity_id=entity_id, mailbox_id=mailbox_id)

    async def count_customer_links(self, *, mailbox_id: int) -> int:
        return await self._repo.count_customer_links(mailbox_id=mailbox_id)

    async def link_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int):
        return await self._repo.link_customer(
            entity_id=entity_id, mailbox_id=mailbox_id, customer_id=customer_id
        )

    async def unlink_customer(self, *, entity_id: int, mailbox_id: int, customer_id: int) -> None:
        await self._repo.unlink_customer(
            entity_id=entity_id, mailbox_id=mailbox_id, customer_id=customer_id
        )
