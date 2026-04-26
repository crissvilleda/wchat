from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel

if False:
    from .customer import Customer
    from .mailbox import Mailbox


class CustomerMailbox(AuditedSoftDeleteModel):
    __tablename__ = "customer_mailbox"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "mailbox_id",
            name="uq_customer_mailbox_pair",
        ),
    )

    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mailbox_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("mailbox.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="customer_mailbox_links",
    )
    mailbox: Mapped["Mailbox"] = relationship(
        back_populates="customer_links",
    )
