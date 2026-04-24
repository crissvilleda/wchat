from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel


class MailboxCredential(AuditedSoftDeleteModel):
    __tablename__ = "mailbox_credential"

    # 1:1 with StreamingAccount
    streaming_account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("streaming_account.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    mailbox_address: Mapped[str] = mapped_column(String(320), nullable=False)

    # Storage strategy is finalized in the "secrets" todo.
    # For now we support either a structured payload or a secret reference.
    credential_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Recommended: store a reference to a secret manager entry (e.g. Azure Key Vault),
    # not the raw refresh token / password in the database.
    secret_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)

    token_scopes: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    streaming_account: Mapped["StreamingAccount"] = relationship(back_populates="mailbox_credential")

