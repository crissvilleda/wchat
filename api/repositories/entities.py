from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError
from orm_models.entity import Entity


class DbEntityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, name: str) -> Entity:
        entity = Entity(name=name)
        self._db.add(entity)
        try:
            await self._db.commit()
        except IntegrityError as e:
            await self._db.rollback()
            raise ConflictError("Entity already exists") from e
        await self._db.refresh(entity)
        return entity

