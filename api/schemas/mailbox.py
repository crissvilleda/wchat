from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from api.schemas.common import AuditedOut


class MailboxCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    mailbox_address: str = Field(min_length=3, max_length=320)
    credential_payload: dict | None = None
    secret_ref: str | None = Field(default=None, max_length=512)
    token_scopes: str | None = Field(default=None, max_length=2048)
    token_expiry: datetime | None = None
    max_customer_links: int | None = Field(default=None, ge=1)


class MailboxUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=32)
    mailbox_address: str | None = Field(default=None, min_length=3, max_length=320)
    credential_payload: dict | None = None
    secret_ref: str | None = Field(default=None, max_length=512)
    token_scopes: str | None = Field(default=None, max_length=2048)
    token_expiry: datetime | None = None
    revoked_at: datetime | None = None
    max_customer_links: int | None = Field(default=None, ge=1)


class MailboxOut(AuditedOut):
    entity_id: int
    provider: str
    mailbox_address: str
    credential_payload: dict | None
    secret_ref: str | None
    token_scopes: str | None
    token_expiry: datetime | None
    revoked_at: datetime | None
    max_customer_links: int | None
    current_customer_link_count: int
