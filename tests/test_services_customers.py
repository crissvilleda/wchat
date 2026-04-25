from __future__ import annotations

import pytest

from api.pagination.cursor import encode_id_cursor
from api.repositories.errors import ConflictError, NotFoundError
from api.services.customers_service import CustomersService
from tests.conftest import CallRecorder


class _FakeCustomerRepo(CallRecorder):
    async def create(self, *, entity_id: int, name: str, whatsapp_e164: str):
        self.record("create", {"entity_id": entity_id, "name": name, "whatsapp_e164": whatsapp_e164})
        self.maybe_raise("create")
        return self.value("create")

    async def get(self, *, entity_id: int, customer_id: int):
        self.record("get", {"entity_id": entity_id, "customer_id": customer_id})
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, *, entity_id: int, limit: int, after_id: int | None, q: str | None):
        self.record(
            "list",
            {"entity_id": entity_id, "limit": limit, "after_id": after_id, "q": q},
        )
        self.maybe_raise("list")
        return self.value("list")

    async def update(
        self, *, entity_id: int, customer_id: int, name: str | None, whatsapp_e164: str | None
    ):
        self.record(
            "update",
            {
                "entity_id": entity_id,
                "customer_id": customer_id,
                "name": name,
                "whatsapp_e164": whatsapp_e164,
            },
        )
        self.maybe_raise("update")
        return self.value("update")

    async def soft_delete(self, *, entity_id: int, customer_id: int) -> None:
        self.record("soft_delete", {"entity_id": entity_id, "customer_id": customer_id})
        self.maybe_raise("soft_delete")
        return None


@pytest.mark.asyncio
async def test_customers_service_create_forwards_args_and_returns_value():
    repo = _FakeCustomerRepo(return_values={"create": object()})
    service = CustomersService(repo)

    out = await service.create(entity_id=1, name="C", whatsapp_e164="+15551234567")

    assert out is repo.return_values["create"]
    assert repo.calls == [("create", {"entity_id": 1, "name": "C", "whatsapp_e164": "+15551234567"})]


@pytest.mark.asyncio
async def test_customers_service_create_propagates_conflict():
    repo = _FakeCustomerRepo(side_effects={"create": ConflictError("dup")})
    service = CustomersService(repo)

    with pytest.raises(ConflictError):
        await service.create(entity_id=1, name="C", whatsapp_e164="+15551234567")


@pytest.mark.asyncio
async def test_customers_service_get_forwards_args_and_returns_value():
    repo = _FakeCustomerRepo(return_values={"get": object()})
    service = CustomersService(repo)

    out = await service.get(entity_id=2, customer_id=3)

    assert out is repo.return_values["get"]
    assert repo.calls == [("get", {"entity_id": 2, "customer_id": 3})]


@pytest.mark.asyncio
async def test_customers_service_get_propagates_not_found():
    repo = _FakeCustomerRepo(side_effects={"get": NotFoundError("no")})
    service = CustomersService(repo)

    with pytest.raises(NotFoundError):
        await service.get(entity_id=2, customer_id=3)


@pytest.mark.asyncio
async def test_customers_service_list_forwards_args_and_encodes_next_cursor():
    rows = [object()]
    repo = _FakeCustomerRepo(return_values={"list": (rows, 3)})
    service = CustomersService(repo)

    out_items, out_cursor = await service.list(
        entity_id=7, limit=10, after_id=None, q=None
    )

    assert out_items is rows
    assert out_cursor == encode_id_cursor(3)
    assert repo.calls == [("list", {"entity_id": 7, "limit": 10, "after_id": None, "q": None})]


@pytest.mark.asyncio
async def test_customers_service_update_forwards_none_fields():
    repo = _FakeCustomerRepo(return_values={"update": object()})
    service = CustomersService(repo)

    out = await service.update(entity_id=1, customer_id=2, name=None, whatsapp_e164=None)

    assert out is repo.return_values["update"]
    assert repo.calls == [
        ("update", {"entity_id": 1, "customer_id": 2, "name": None, "whatsapp_e164": None})
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [NotFoundError("nf"), ConflictError("conf")])
async def test_customers_service_update_propagates_errors(exc: Exception):
    repo = _FakeCustomerRepo(side_effects={"update": exc})
    service = CustomersService(repo)

    with pytest.raises(type(exc)):
        await service.update(entity_id=1, customer_id=2, name="N", whatsapp_e164=None)


@pytest.mark.asyncio
async def test_customers_service_soft_delete_forwards_args():
    repo = _FakeCustomerRepo()
    service = CustomersService(repo)

    out = await service.soft_delete(entity_id=1, customer_id=2)

    assert out is None
    assert repo.calls == [("soft_delete", {"entity_id": 1, "customer_id": 2})]

