from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class EntityIsolationModel:
    """
    Tenant isolation mixin.

    This intentionally does NOT include auditing / soft-delete fields.
    Use multiple inheritance with `AuditedSoftDeleteModel` on mapped models.
    """

    __abstract__ = True

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entity.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

