from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from .base import AuditedSoftDeleteModel
from .entity_isolation import EntityIsolationModel
from .mailbox_provider import MailboxProvider

if TYPE_CHECKING:
    from .customer_mailbox import CustomerMailbox


class Mailbox(EntityIsolationModel, AuditedSoftDeleteModel):
    __tablename__ = "mailbox"
    __table_args__ = (
        UniqueConstraint("entity_id", "mailbox_address", name="uq_mailbox_entity_address"),
        Index(
            "ix_mailbox_mailbox_address_trgm",
            "mailbox_address",
            postgresql_using="gin",
            postgresql_ops={"mailbox_address": "gin_trgm_ops"},
        ),
        Index(
            "ix_mailbox_provider_trgm",
            "provider",
            postgresql_using="gin",
            postgresql_ops={"provider": "gin_trgm_ops"},
        ),
    )

    provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MailboxProvider.GMAIL.value,
    )
    mailbox_address: Mapped[str] = mapped_column(String(320), nullable=False)

    credential_payload: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSON), nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_scopes: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    max_customer_links: Mapped[int | None] = mapped_column(Integer, nullable=True)

    entity: Mapped["Entity"] = relationship(back_populates="mailboxes")
    customer_links: Mapped[list["CustomerMailbox"]] = relationship(
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )
    entitlements: Mapped[list["CustomerStreamingEntitlement"]] = relationship(
        back_populates="mailbox",
    )
