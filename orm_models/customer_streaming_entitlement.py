from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel


class CustomerStreamingEntitlement(AuditedSoftDeleteModel):
    __tablename__ = "customer_streaming_entitlement"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "streaming_service_id",
            name="uq_customer_streaming_entitlements_customer_service",
        ),
    )

    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    streaming_service_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("streaming_service.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    mailbox_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("mailbox.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Keep as string for flexibility (active/suspended/etc.).
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    customer: Mapped["Customer"] = relationship(back_populates="entitlements")
    streaming_service: Mapped["StreamingService"] = relationship(back_populates="entitlements")
    mailbox: Mapped["Mailbox | None"] = relationship(back_populates="entitlements")

