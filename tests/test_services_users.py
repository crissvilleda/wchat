from __future__ import annotations

import pytest

from api.repositories.errors import ConflictError, NotFoundError
from api.services.users_service import UsersService
from tests.conftest import CallRecorder


class _FakeUserRepo(CallRecorder):
    async def create(self, *, entity_id: int, name: str, email: str, supertokens_user_id: str):
        self.record(
            "create",
            {
                "entity_id": entity_id,
                "name": name,
                "email": email,
                "supertokens_user_id": supertokens_user_id,
            },
        )
        self.maybe_raise("create")
        return self.value("create")

    async def get(self, *, entity_id: int, user_id: int):
        self.record("get", {"entity_id": entity_id, "user_id": user_id})
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, *, entity_id: int, limit: int, offset: int):
        self.record("list", {"entity_id": entity_id, "limit": limit, "offset": offset})
        self.maybe_raise("list")
        return self.value("list")

    async def update(self, *, entity_id: int, user_id: int, name: str | None, email: str | None):
        self.record(
            "update",
            {"entity_id": entity_id, "user_id": user_id, "name": name, "email": email},
        )
        self.maybe_raise("update")
        return self.value("update")

    async def soft_delete(self, *, entity_id: int, user_id: int) -> None:
        self.record("soft_delete", {"entity_id": entity_id, "user_id": user_id})
        self.maybe_raise("soft_delete")
        return None


@pytest.mark.asyncio
async def test_users_service_create_forwards_args_and_returns_value():
    repo = _FakeUserRepo(return_values={"create": object()})
    service = UsersService(repo)

    out = await service.create(entity_id=1, name="A", email="a@example.com", supertokens_user_id="st_1")

    assert out is repo.return_values["create"]
    assert repo.calls == [
        (
            "create",
            {"entity_id": 1, "name": "A", "email": "a@example.com", "supertokens_user_id": "st_1"},
        )
    ]


@pytest.mark.asyncio
async def test_users_service_create_propagates_conflict():
    repo = _FakeUserRepo(side_effects={"create": ConflictError("boom")})
    service = UsersService(repo)

    with pytest.raises(ConflictError):
        await service.create(entity_id=1, name="A", email="a@example.com", supertokens_user_id="st_1")


@pytest.mark.asyncio
async def test_users_service_get_forwards_args_and_returns_value():
    repo = _FakeUserRepo(return_values={"get": object()})
    service = UsersService(repo)

    out = await service.get(entity_id=9, user_id=10)

    assert out is repo.return_values["get"]
    assert repo.calls == [("get", {"entity_id": 9, "user_id": 10})]


@pytest.mark.asyncio
async def test_users_service_get_propagates_not_found():
    repo = _FakeUserRepo(side_effects={"get": NotFoundError("nope")})
    service = UsersService(repo)

    with pytest.raises(NotFoundError):
        await service.get(entity_id=9, user_id=10)


@pytest.mark.asyncio
async def test_users_service_list_forwards_args_and_returns_value():
    rows = [object(), object()]
    repo = _FakeUserRepo(return_values={"list": rows})
    service = UsersService(repo)

    out = await service.list(entity_id=2, limit=50, offset=100)

    assert out is rows
    assert repo.calls == [("list", {"entity_id": 2, "limit": 50, "offset": 100})]


@pytest.mark.asyncio
async def test_users_service_update_forwards_none_fields():
    repo = _FakeUserRepo(return_values={"update": object()})
    service = UsersService(repo)

    out = await service.update(entity_id=1, user_id=2, name=None, email="x@example.com")

    assert out is repo.return_values["update"]
    assert repo.calls == [
        ("update", {"entity_id": 1, "user_id": 2, "name": None, "email": "x@example.com"})
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [NotFoundError("nf"), ConflictError("conf")])
async def test_users_service_update_propagates_errors(exc: Exception):
    repo = _FakeUserRepo(side_effects={"update": exc})
    service = UsersService(repo)

    with pytest.raises(type(exc)):
        await service.update(entity_id=1, user_id=2, name="N", email=None)


@pytest.mark.asyncio
async def test_users_service_soft_delete_forwards_args():
    repo = _FakeUserRepo()
    service = UsersService(repo)

    out = await service.soft_delete(entity_id=1, user_id=2)

    assert out is None
    assert repo.calls == [("soft_delete", {"entity_id": 1, "user_id": 2})]

