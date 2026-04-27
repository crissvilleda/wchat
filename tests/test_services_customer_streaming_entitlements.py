from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from api.repositories.errors import NotFoundError
from api.schemas.customer_streaming_entitlements_sync import (
    CustomerStreamingEntitlementAssignmentIn,
)
from api.services.customer_streaming_entitlements_service import CustomerStreamingEntitlementsService
from tests.conftest import CallRecorder


class _NoopMailboxRepo:
    async def ensure_customer_mailbox_link(self, *args, **kwargs) -> None:
        return None

    async def prune_orphan_customer_mailbox_links(self, *args, **kwargs) -> None:
        return None


class _FakeCustomerStreamingEntitlementRepo(CallRecorder):
    async def upsert(
        self,
        *,
        entity_id: int,
        customer_id: int,
        streaming_service_id: int,
        mailbox_id: int,
    ):
        self.record(
            "upsert",
            {
                "entity_id": entity_id,
                "customer_id": customer_id,
                "streaming_service_id": streaming_service_id,
                "mailbox_id": mailbox_id,
            },
        )
        self.maybe_raise("upsert")
        return self.value("upsert")

    async def soft_delete(
        self, *, entity_id: int, customer_id: int, streaming_service_id: int
    ) -> None:
        raise AssertionError("not used in these tests")

    async def soft_delete_entitlements_not_in(
        self,
        *,
        entity_id: int,
        customer_id: int,
        keep_streaming_service_ids: set[int],
    ) -> None:
        self.record(
            "soft_delete_entitlements_not_in",
            {
                "entity_id": entity_id,
                "customer_id": customer_id,
                "keep_streaming_service_ids": keep_streaming_service_ids,
            },
        )
        self.maybe_raise("soft_delete_entitlements_not_in")

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
    ent = SimpleNamespace(id=100, mailbox=mb)
    s1 = _service(1, "netflix", "Netflix")
    s2 = _service(2, "disney", "Disney+")
    repo.return_values["list_assignments_for_customer"] = [
        (s1, ent),
        (s2, None),
    ]

    svc = CustomerStreamingEntitlementsService(repo, _NoopMailboxRepo())
    rows = await svc.list_assignments_for_customer(entity_id=1, customer_id=5)

    assert repo.calls == [
        ("list_assignments_for_customer", {"entity_id": 1, "customer_id": 5}),
    ]
    assert len(rows) == 2
    assert rows[0].streaming_service.slug == "netflix"
    assert rows[0].entitlement is not None and rows[0].entitlement.id == 100
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
    ent1 = SimpleNamespace(id=101, mailbox=mb_wrong_entity)
    ent2 = SimpleNamespace(id=102, mailbox=mb_deleted)
    repo.return_values["list_assignments_for_customer"] = [
        (_service(1, "a", "A"), ent1),
        (_service(2, "b", "B"), ent2),
    ]

    svc = CustomerStreamingEntitlementsService(repo, _NoopMailboxRepo())
    rows = await svc.list_assignments_for_customer(entity_id=1, customer_id=1)

    assert rows[0].entitlement is not None and rows[0].mailbox is None
    assert rows[1].entitlement is not None and rows[1].mailbox is None


@pytest.mark.asyncio
async def test_list_assignments_propagates_not_found():
    repo = _FakeCustomerStreamingEntitlementRepo()
    repo.side_effects["list_assignments_for_customer"] = NotFoundError("Customer not found")

    svc = CustomerStreamingEntitlementsService(repo, _NoopMailboxRepo())
    with pytest.raises(NotFoundError):
        await svc.list_assignments_for_customer(entity_id=1, customer_id=3)


class _FakeMailboxRepoForSync(CallRecorder):
    async def ensure_customer_mailbox_link(
        self, *, entity_id: int, mailbox_id: int, customer_id: int
    ) -> None:
        self.record(
            "ensure_customer_mailbox_link",
            {
                "entity_id": entity_id,
                "mailbox_id": mailbox_id,
                "customer_id": customer_id,
            },
        )
        self.maybe_raise("ensure_customer_mailbox_link")

    async def prune_orphan_customer_mailbox_links(
        self, *, entity_id: int, customer_id: int
    ) -> None:
        self.record(
            "prune_orphan_customer_mailbox_links",
            {"entity_id": entity_id, "customer_id": customer_id},
        )
        self.maybe_raise("prune_orphan_customer_mailbox_links")


@pytest.mark.asyncio
async def test_sync_assignments_order_and_final_list():
    ent_repo = _FakeCustomerStreamingEntitlementRepo()
    mb_repo = _FakeMailboxRepoForSync()
    ent_repo.return_values["list_assignments_for_customer"] = []

    svc = CustomerStreamingEntitlementsService(ent_repo, mb_repo)
    assignments = [
        CustomerStreamingEntitlementAssignmentIn(streaming_service_id=1, mailbox_id=10),
        CustomerStreamingEntitlementAssignmentIn(streaming_service_id=2, mailbox_id=10),
    ]
    out = await svc.sync_assignments(
        entity_id=7, customer_id=5, assignments=assignments
    )

    assert out == []
    assert ent_repo.calls[0] == (
        "soft_delete_entitlements_not_in",
        {
            "entity_id": 7,
            "customer_id": 5,
            "keep_streaming_service_ids": {1, 2},
        },
    )
    assert mb_repo.calls[0] == (
        "ensure_customer_mailbox_link",
        {"entity_id": 7, "mailbox_id": 10, "customer_id": 5},
    )
    assert ent_repo.calls[1] == (
        "upsert",
        {
            "entity_id": 7,
            "customer_id": 5,
            "streaming_service_id": 1,
            "mailbox_id": 10,
        },
    )
    assert mb_repo.calls[1] == (
        "ensure_customer_mailbox_link",
        {"entity_id": 7, "mailbox_id": 10, "customer_id": 5},
    )
    assert ent_repo.calls[2] == (
        "upsert",
        {
            "entity_id": 7,
            "customer_id": 5,
            "streaming_service_id": 2,
            "mailbox_id": 10,
        },
    )
    assert mb_repo.calls[2] == (
        "prune_orphan_customer_mailbox_links",
        {"entity_id": 7, "customer_id": 5},
    )
    assert ent_repo.calls[3] == (
        "list_assignments_for_customer",
        {"entity_id": 7, "customer_id": 5},
    )


def test_sync_schema_rejects_duplicate_streaming_service():
    from pydantic import ValidationError

    from api.schemas.customer_streaming_entitlements_sync import (
        CustomerStreamingEntitlementsSync,
    )

    with pytest.raises(ValidationError):
        CustomerStreamingEntitlementsSync(
            assignments=[
                CustomerStreamingEntitlementAssignmentIn(
                    streaming_service_id=1, mailbox_id=1
                ),
                CustomerStreamingEntitlementAssignmentIn(
                    streaming_service_id=1, mailbox_id=2
                ),
            ]
        )
