from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError
from orm_models.entity import Entity

logger = logging.getLogger(__name__)


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
            orig = getattr(e, "orig", None)
            pgcode = getattr(orig, "pgcode", None)
            constraint = getattr(getattr(orig, "diag", None), "constraint_name", None)
            logger.exception(
                "db_integrity_error",
                extra={
                    "domain": "db",
                    "op": "entity.create",
                    "pgcode": pgcode,
                    "constraint": constraint,
                },
            )
            raise ConflictError("Entity already exists") from e
        await self._db.refresh(entity)
        return entity

