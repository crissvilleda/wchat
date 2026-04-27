from __future__ import annotations

from pydantic import BaseModel


class CustomerStreamingEntitlementUpsert(BaseModel):
    mailbox_id: int
