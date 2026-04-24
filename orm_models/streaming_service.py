from __future__ import annotations

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel


class StreamingService(AuditedSoftDeleteModel):
    __tablename__ = "streaming_service"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_streaming_services_slug"),
    )

    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Keyword patterns for message matching (simple storage).
    # Example: ["netflix", "nf", "net flix"]
    keyword_patterns: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    entitlements: Mapped[list["CustomerStreamingEntitlement"]] = relationship(back_populates="streaming_service")
    streaming_accounts: Mapped[list["StreamingAccount"]] = relationship(back_populates="streaming_service")

