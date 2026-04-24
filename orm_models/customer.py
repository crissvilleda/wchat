from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel
from .entity_isolation import EntityIsolationModel


class Customer(EntityIsolationModel, AuditedSoftDeleteModel):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint("entity_id", "whatsapp_e164", name="uq_customers_entity_whatsapp_e164"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp_e164: Mapped[str] = mapped_column(String(32), nullable=False)

    entity: Mapped["Entity"] = relationship(back_populates="customers")
    entitlements: Mapped[list["CustomerStreamingEntitlement"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

