from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from orm_models.user import User


class UserRepository(Protocol):
    async def create(self, *, entity_id: int, name: str, email: str, supertokens_user_id: str) -> User: ...
    async def get(self, *, entity_id: int, user_id: int) -> User: ...
    async def list(self, *, entity_id: int, limit: int, offset: int) -> Sequence[User]: ...
    async def update(self, *, entity_id: int, user_id: int, name: str | None, email: str | None) -> User: ...
    async def soft_delete(self, *, entity_id: int, user_id: int) -> None: ...


class DbUserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, entity_id: int, name: str, email: str, supertokens_user_id: str) -> User:
        user = User(entity_id=entity_id, name=name, email=email, supertokens_user_id=supertokens_user_id)
        self._db.add(user)
        try:
            await self._db.commit()
        except IntegrityError as e:
            await self._db.rollback()
            raise ConflictError("User already exists") from e
        await self._db.refresh(user)
        return user

    async def get(self, *, entity_id: int, user_id: int) -> User:
        stmt = select(User).where(
            User.id == user_id,
            User.entity_id == entity_id,
            User.deleted_at.is_(None),
        )
        user = (await self._db.execute(stmt)).scalars().first()
        if not user:
            raise NotFoundError("User not found")
        return user

    async def list(self, *, entity_id: int, limit: int, offset: int) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.entity_id == entity_id, User.deleted_at.is_(None))
            .order_by(User.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def update(self, *, entity_id: int, user_id: int, name: str | None, email: str | None) -> User:
        user = await self.get(entity_id=entity_id, user_id=user_id)
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        try:
            await self._db.commit()
        except IntegrityError as e:
            await self._db.rollback()
            raise ConflictError("Update conflict") from e
        await self._db.refresh(user)
        return user

    async def soft_delete(self, *, entity_id: int, user_id: int) -> None:
        user = await self.get(entity_id=entity_id, user_id=user_id)
        user.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.commit()

