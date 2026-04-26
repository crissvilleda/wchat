from __future__ import annotations

import pytest

from api.pagination.cursor import encode_id_cursor
from api.repositories.errors import NotFoundError
from api.services.streaming_services_service import StreamingServicesService
from tests.conftest import CallRecorder


class _FakeStreamingServiceRepo(CallRecorder):
    async def get(self, *, service_id: int):
        self.record("get", {"service_id": service_id})
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, *, limit: int, after_id: int | None, q: str | None):
        self.record("list", {"limit": limit, "after_id": after_id, "q": q})
        self.maybe_raise("list")
        return self.value("list")


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
async def test_streaming_services_service_list_forwards_args_and_encodes_next_cursor():
    rows = [object(), object()]
    repo = _FakeStreamingServiceRepo(return_values={"list": (rows, 9)})
    service = StreamingServicesService(repo)

    out_items, out_cursor = await service.list(limit=10, after_id=2, q="net")

    assert out_items is rows
    assert out_cursor == encode_id_cursor(9)
    assert repo.calls == [("list", {"limit": 10, "after_id": 2, "q": "net"})]
