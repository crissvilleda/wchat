from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditedSoftDeleteModel
from .entity_isolation import EntityIsolationModel


class User(EntityIsolationModel, AuditedSoftDeleteModel):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("supertokens_user_id", name="uq_users_supertokens_user_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    supertokens_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    entity: Mapped["Entity"] = relationship(back_populates="users")

