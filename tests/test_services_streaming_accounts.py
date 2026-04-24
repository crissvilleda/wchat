from __future__ import annotations

import pytest

from api.repositories.errors import ConflictError, NotFoundError
from api.services.streaming_accounts_service import StreamingAccountsService
from tests.conftest import CallRecorder


class _FakeStreamingAccountRepo(CallRecorder):
    async def create(self, *, entity_id: int, streaming_service_id: int, label: str, is_active: bool):
        self.record(
            "create",
            {
                "entity_id": entity_id,
                "streaming_service_id": streaming_service_id,
                "label": label,
                "is_active": is_active,
            },
        )
        self.maybe_raise("create")
        return self.value("create")

    async def get(self, *, entity_id: int, streaming_account_id: int):
        self.record("get", {"entity_id": entity_id, "streaming_account_id": streaming_account_id})
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, *, entity_id: int, limit: int, offset: int):
        self.record("list", {"entity_id": entity_id, "limit": limit, "offset": offset})
        self.maybe_raise("list")
        return self.value("list")

    async def update(
        self,
        *,
        entity_id: int,
        streaming_account_id: int,
        streaming_service_id: int | None,
        label: str | None,
        is_active: bool | None,
    ):
        self.record(
            "update",
            {
                "entity_id": entity_id,
                "streaming_account_id": streaming_account_id,
                "streaming_service_id": streaming_service_id,
                "label": label,
                "is_active": is_active,
            },
        )
        self.maybe_raise("update")
        return self.value("update")

    async def soft_delete(self, *, entity_id: int, streaming_account_id: int) -> None:
        self.record("soft_delete", {"entity_id": entity_id, "streaming_account_id": streaming_account_id})
        self.maybe_raise("soft_delete")
        return None


@pytest.mark.asyncio
async def test_streaming_accounts_service_create_forwards_args_and_returns_value():
    repo = _FakeStreamingAccountRepo(return_values={"create": object()})
    service = StreamingAccountsService(repo)

    out = await service.create(entity_id=1, streaming_service_id=2, label="Main", is_active=True)

    assert out is repo.return_values["create"]
    assert repo.calls == [
        (
            "create",
            {"entity_id": 1, "streaming_service_id": 2, "label": "Main", "is_active": True},
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [NotFoundError("nf"), ConflictError("conf")])
async def test_streaming_accounts_service_create_propagates_errors(exc: Exception):
    repo = _FakeStreamingAccountRepo(side_effects={"create": exc})
    service = StreamingAccountsService(repo)

    with pytest.raises(type(exc)):
        await service.create(entity_id=1, streaming_service_id=2, label="Main", is_active=True)


@pytest.mark.asyncio
async def test_streaming_accounts_service_get_forwards_args_and_returns_value():
    repo = _FakeStreamingAccountRepo(return_values={"get": object()})
    service = StreamingAccountsService(repo)

    out = await service.get(entity_id=1, streaming_account_id=10)

    assert out is repo.return_values["get"]
    assert repo.calls == [("get", {"entity_id": 1, "streaming_account_id": 10})]


@pytest.mark.asyncio
async def test_streaming_accounts_service_get_propagates_not_found():
    repo = _FakeStreamingAccountRepo(side_effects={"get": NotFoundError("no")})
    service = StreamingAccountsService(repo)

    with pytest.raises(NotFoundError):
        await service.get(entity_id=1, streaming_account_id=10)


@pytest.mark.asyncio
async def test_streaming_accounts_service_list_forwards_args_and_returns_value():
    rows = [object()]
    repo = _FakeStreamingAccountRepo(return_values={"list": rows})
    service = StreamingAccountsService(repo)

    out = await service.list(entity_id=1, limit=50, offset=0)

    assert out is rows
    assert repo.calls == [("list", {"entity_id": 1, "limit": 50, "offset": 0})]


@pytest.mark.asyncio
async def test_streaming_accounts_service_update_forwards_optional_fields():
    repo = _FakeStreamingAccountRepo(return_values={"update": object()})
    service = StreamingAccountsService(repo)

    out = await service.update(
        entity_id=1,
        streaming_account_id=10,
        streaming_service_id=None,
        label="X",
        is_active=None,
    )

    assert out is repo.return_values["update"]
    assert repo.calls == [
        (
            "update",
            {
                "entity_id": 1,
                "streaming_account_id": 10,
                "streaming_service_id": None,
                "label": "X",
                "is_active": None,
            },
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [NotFoundError("nf"), ConflictError("conf")])
async def test_streaming_accounts_service_update_propagates_errors(exc: Exception):
    repo = _FakeStreamingAccountRepo(side_effects={"update": exc})
    service = StreamingAccountsService(repo)

    with pytest.raises(type(exc)):
        await service.update(
            entity_id=1,
            streaming_account_id=10,
            streaming_service_id=99,
            label=None,
            is_active=True,
        )


@pytest.mark.asyncio
async def test_streaming_accounts_service_soft_delete_forwards_args():
    repo = _FakeStreamingAccountRepo()
    service = StreamingAccountsService(repo)

    out = await service.soft_delete(entity_id=1, streaming_account_id=10)

    assert out is None
    assert repo.calls == [("soft_delete", {"entity_id": 1, "streaming_account_id": 10})]

