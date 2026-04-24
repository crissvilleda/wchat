from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    pass


class AuditedSoftDeleteModel(BaseModel):
    __abstract__ = True

    # SQLite autoincrement works reliably with INTEGER PRIMARY KEY; keep BIGINT for Postgres.
    id: Mapped[int] = mapped_column(
        BigInteger()
        .with_variant(Integer(), "sqlite")
        .with_variant(Integer(), "aiosqlite"),
        primary_key=True,
        autoincrement=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
