from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel
from .entity_isolation import EntityIsolationModel


class StreamingAccount(EntityIsolationModel, AuditedSoftDeleteModel):
    __tablename__ = "streaming_account"
    __table_args__ = (
        UniqueConstraint(
            "entity_id",
            "streaming_service_id",
            "label",
            name="uq_streaming_accounts_entity_service_label",
        ),
    )

    streaming_service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("streaming_service.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    entity: Mapped["Entity"] = relationship(back_populates="streaming_accounts")
    streaming_service: Mapped["StreamingService"] = relationship(back_populates="streaming_accounts")
    mailbox_credential: Mapped["MailboxCredential | None"] = relationship(
        back_populates="streaming_account",
        uselist=False,
        cascade="all, delete-orphan",
    )

