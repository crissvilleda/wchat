from __future__ import annotations

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel
from .entity_isolation import EntityIsolationModel


class Customer(EntityIsolationModel, AuditedSoftDeleteModel):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint("entity_id", "whatsapp_e164", name="uq_customers_entity_whatsapp_e164"),
        Index(
            "ix_customer_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_customer_whatsapp_e164_trgm",
            "whatsapp_e164",
            postgresql_using="gin",
            postgresql_ops={"whatsapp_e164": "gin_trgm_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp_e164: Mapped[str] = mapped_column(String(32), nullable=False)

    entity: Mapped["Entity"] = relationship(back_populates="customers")
    customer_mailbox_links: Mapped[list["CustomerMailbox"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    entitlements: Mapped[list["CustomerStreamingEntitlement"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

