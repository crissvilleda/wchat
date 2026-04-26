from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel


class Entity(AuditedSoftDeleteModel):
    __tablename__ = "entity"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="entity")
    customers: Mapped[list["Customer"]] = relationship(back_populates="entity")
    mailboxes: Mapped[list["Mailbox"]] = relationship(back_populates="entity")

