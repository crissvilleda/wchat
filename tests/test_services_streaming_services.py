from __future__ import annotations

import pytest

from api.repositories.errors import ConflictError, NotFoundError
from api.services.streaming_services_service import StreamingServicesService
from tests.conftest import CallRecorder


class _FakeStreamingServiceRepo(CallRecorder):
    async def create(self, *, slug: str, display_name: str, keyword_patterns: list[str] | None):
        self.record("create", {"slug": slug, "display_name": display_name, "keyword_patterns": keyword_patterns})
        self.maybe_raise("create")
        return self.value("create")

    async def get(self, *, service_id: int):
        self.record("get", {"service_id": service_id})
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, *, limit: int, offset: int):
        self.record("list", {"limit": limit, "offset": offset})
        self.maybe_raise("list")
        return self.value("list")

    async def update(self, *, service_id: int, display_name: str | None, keyword_patterns: list[str] | None):
        self.record(
            "update",
            {"service_id": service_id, "display_name": display_name, "keyword_patterns": keyword_patterns},
        )
        self.maybe_raise("update")
        return self.value("update")

    async def soft_delete(self, *, service_id: int) -> None:
        self.record("soft_delete", {"service_id": service_id})
        self.maybe_raise("soft_delete")
        return None


@pytest.mark.asyncio
async def test_streaming_services_service_create_forwards_args_and_returns_value():
    repo = _FakeStreamingServiceRepo(return_values={"create": object()})
    service = StreamingServicesService(repo)

    out = await service.create(slug="netflix", display_name="Netflix", keyword_patterns=None)

    assert out is repo.return_values["create"]
    assert repo.calls == [("create", {"slug": "netflix", "display_name": "Netflix", "keyword_patterns": None})]


@pytest.mark.asyncio
async def test_streaming_services_service_create_propagates_conflict():
    repo = _FakeStreamingServiceRepo(side_effects={"create": ConflictError("dup")})
    service = StreamingServicesService(repo)

    with pytest.raises(ConflictError):
        await service.create(slug="netflix", display_name="Netflix", keyword_patterns=None)


@pytest.mark.asyncio
async def test_streaming_services_service_get_forwards_args_and_returns_value():
    repo = _FakeStreamingServiceRepo(return_values={"get": object()})
    service = StreamingServicesService(repo)

    out = await service.get(service_id=1)

    assert out is repo.return_values["get"]
    assert repo.calls == [("get", {"service_id": 1})]


@pytest.mark.asyncio
async def test_streaming_services_service_get_propagates_not_found():
    repo = _FakeStreamingServiceRepo(side_effects={"get": NotFoundError("no")})
    service = StreamingServicesService(repo)

    with pytest.raises(NotFoundError):
        await service.get(service_id=1)


@pytest.mark.asyncio
async def test_streaming_services_service_list_forwards_args_and_returns_value():
    rows = [object(), object()]
    repo = _FakeStreamingServiceRepo(return_values={"list": rows})
    service = StreamingServicesService(repo)

    out = await service.list(limit=10, offset=5)

    assert out is rows
    assert repo.calls == [("list", {"limit": 10, "offset": 5})]


@pytest.mark.asyncio
async def test_streaming_services_service_update_forwards_args_and_returns_value():
    repo = _FakeStreamingServiceRepo(return_values={"update": object()})
    service = StreamingServicesService(repo)

    out = await service.update(service_id=2, display_name=None, keyword_patterns=["nf"])

    assert out is repo.return_values["update"]
    assert repo.calls == [
        ("update", {"service_id": 2, "display_name": None, "keyword_patterns": ["nf"]})
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [NotFoundError("nf"), ConflictError("conf")])
async def test_streaming_services_service_update_propagates_errors(exc: Exception):
    repo = _FakeStreamingServiceRepo(side_effects={"update": exc})
    service = StreamingServicesService(repo)

    with pytest.raises(type(exc)):
        await service.update(service_id=2, display_name="X", keyword_patterns=None)


@pytest.mark.asyncio
async def test_streaming_services_service_soft_delete_forwards_args():
    repo = _FakeStreamingServiceRepo()
    service = StreamingServicesService(repo)

    out = await service.soft_delete(service_id=2)

    assert out is None
    assert repo.calls == [("soft_delete", {"service_id": 2})]

