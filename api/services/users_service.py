from __future__ import annotations

from collections.abc import Sequence

from api.repositories.users import UserRepository
from orm_models.user import User


class UsersService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def create(self, *, entity_id: int, name: str, email: str, supertokens_user_id: str) -> User:
        return await self._repo.create(
            entity_id=entity_id,
            name=name,
            email=email,
            supertokens_user_id=supertokens_user_id,
        )

    async def get(self, *, entity_id: int, user_id: int) -> User:
        return await self._repo.get(entity_id=entity_id, user_id=user_id)

    async def list(self, *, entity_id: int, limit: int, offset: int) -> Sequence[User]:
        return await self._repo.list(entity_id=entity_id, limit=limit, offset=offset)

    async def update(self, *, entity_id: int, user_id: int, name: str | None, email: str | None) -> User:
        return await self._repo.update(entity_id=entity_id, user_id=user_id, name=name, email=email)

    async def soft_delete(self, *, entity_id: int, user_id: int) -> None:
        await self._repo.soft_delete(entity_id=entity_id, user_id=user_id)

