from __future__ import annotations

from pydantic import BaseModel, Field


class CustomerStreamingEntitlementUpsert(BaseModel):
    mailbox_id: int
    status: str = Field(min_length=1, max_length=32, default="active")
