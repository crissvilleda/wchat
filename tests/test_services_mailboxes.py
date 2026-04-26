from __future__ import annotations

import pytest

from api.pagination.cursor import encode_id_cursor
from api.services.mailboxes_service import MailboxesService
from tests.conftest import CallRecorder


class _FakeMailboxRepo(CallRecorder):
    async def create(self, **kwargs):
        self.record("create", kwargs)
        self.maybe_raise("create")
        return self.value("create")

    async def get(self, **kwargs):
        self.record("get", kwargs)
        self.maybe_raise("get")
        return self.value("get")

    async def list(self, **kwargs):
        self.record("list", kwargs)
        self.maybe_raise("list")
        return self.value("list")

    async def update(self, **kwargs):
        self.record("update", kwargs)
        self.maybe_raise("update")
        return self.value("update")

    async def soft_delete(self, **kwargs):
        self.record("soft_delete", kwargs)
        self.maybe_raise("soft_delete")
        return None

    async def count_customer_links(self, **kwargs):
        self.record("count_customer_links", kwargs)
        return 0

    async def link_customer(self, **kwargs):
        self.record("link_customer", kwargs)
        self.maybe_raise("link_customer")
        return object()

    async def unlink_customer(self, **kwargs):
        self.record("unlink_customer", kwargs)
        self.maybe_raise("unlink_customer")
        return None


@pytest.mark.asyncio
async def test_mailboxes_service_create_forwards_args():
    repo = _FakeMailboxRepo(return_values={"create": object()})
    service = MailboxesService(repo)

    out = await service.create(
        entity_id=1,
        provider="gmail",
        mailbox_address="a@b.com",
        credential_payload=None,
        secret_ref=None,
        token_scopes=None,
        token_expiry=None,
        max_customer_links=3,
    )

    assert out is repo.return_values["create"]
    assert repo.calls[0][0] == "create"


@pytest.mark.asyncio
async def test_mailboxes_service_list_encodes_next_cursor():
    rows = [object()]
    repo = _FakeMailboxRepo(return_values={"list": (rows, 5)})
    service = MailboxesService(repo)

    out_items, cur = await service.list(entity_id=1, limit=10, after_id=None, q=None)
    assert out_items is rows
    assert cur == encode_id_cursor(5)
