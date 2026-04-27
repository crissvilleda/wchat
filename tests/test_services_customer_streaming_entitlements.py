from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from api.repositories.errors import NotFoundError
from api.services.customer_streaming_entitlements_service import CustomerStreamingEntitlementsService
from tests.conftest import CallRecorder


class _FakeCustomerStreamingEntitlementRepo(CallRecorder):
    async def upsert(
        self,
        *,
        entity_id: int,
        customer_id: int,
        streaming_service_id: int,
        mailbox_id: int,
        status: str,
    ):
        raise AssertionError("not used in these tests")

    async def soft_delete(
        self, *, entity_id: int, customer_id: int, streaming_service_id: int
    ) -> None:
        raise AssertionError("not used in these tests")

    async def list_assignments_for_customer(
        self, *, entity_id: int, customer_id: int
    ):
        self.record(
            "list_assignments_for_customer",
            {"entity_id": entity_id, "customer_id": customer_id},
        )
        self.maybe_raise("list_assignments_for_customer")
        return self.value("list_assignments_for_customer")


def _ts() -> datetime:
    return datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)


def _service(
    sid: int, slug: str, name: str, *, kw: list[str] | None = None
) -> SimpleNamespace:
    t = _ts()
    return SimpleNamespace(
        id=sid,
        slug=slug,
        display_name=name,
        keyword_patterns=kw,
        created_at=t,
        updated_at=t,
        deleted_at=None,
    )


@pytest.mark.asyncio
async def test_list_assignments_maps_services_entitlements_and_mailbox():
    repo = _FakeCustomerStreamingEntitlementRepo()
    now = _ts()
    mb = SimpleNamespace(
        id=10,
        provider="gmail",
        mailbox_address="pool@example.com",
        entity_id=1,
        deleted_at=None,
    )
    ent = SimpleNamespace(id=100, status="active", mailbox=mb)
    s1 = _service(1, "netflix", "Netflix")
    s2 = _service(2, "disney", "Disney+")
    repo.return_values["list_assignments_for_customer"] = [
        (s1, ent),
        (s2, None),
    ]

    svc = CustomerStreamingEntitlementsService(repo)
    rows = await svc.list_assignments_for_customer(entity_id=1, customer_id=5)

    assert repo.calls == [
        ("list_assignments_for_customer", {"entity_id": 1, "customer_id": 5}),
    ]
    assert len(rows) == 2
    assert rows[0].streaming_service.slug == "netflix"
    assert rows[0].entitlement is not None and rows[0].entitlement.status == "active"
    assert rows[0].mailbox is not None
    assert rows[0].mailbox.mailbox_address == "pool@example.com"
    assert rows[1].entitlement is None and rows[1].mailbox is None


@pytest.mark.asyncio
async def test_list_assignments_omits_mailbox_when_entity_mismatch_or_deleted():
    repo = _FakeCustomerStreamingEntitlementRepo()
    mb_wrong_entity = SimpleNamespace(
        id=11,
        provider="gmail",
        mailbox_address="x@y.com",
        entity_id=99,
        deleted_at=None,
    )
    mb_deleted = SimpleNamespace(
        id=12,
        provider="gmail",
        mailbox_address="gone@y.com",
        entity_id=1,
        deleted_at=_ts(),
    )
    ent1 = SimpleNamespace(id=101, status="active", mailbox=mb_wrong_entity)
    ent2 = SimpleNamespace(id=102, status="suspended", mailbox=mb_deleted)
    repo.return_values["list_assignments_for_customer"] = [
        (_service(1, "a", "A"), ent1),
        (_service(2, "b", "B"), ent2),
    ]

    svc = CustomerStreamingEntitlementsService(repo)
    rows = await svc.list_assignments_for_customer(entity_id=1, customer_id=1)

    assert rows[0].entitlement is not None and rows[0].mailbox is None
    assert rows[1].entitlement is not None and rows[1].mailbox is None


@pytest.mark.asyncio
async def test_list_assignments_propagates_not_found():
    repo = _FakeCustomerStreamingEntitlementRepo()
    repo.side_effects["list_assignments_for_customer"] = NotFoundError("Customer not found")

    svc = CustomerStreamingEntitlementsService(repo)
    with pytest.raises(NotFoundError):
        await svc.list_assignments_for_customer(entity_id=1, customer_id=3)
