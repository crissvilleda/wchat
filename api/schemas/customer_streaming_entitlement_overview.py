from __future__ import annotations

from pydantic import BaseModel

from api.schemas.streaming_service import StreamingServiceOut


class MailboxLinkOut(BaseModel):
    id: int
    provider: str
    mailbox_address: str


class EntitlementLinkOut(BaseModel):
    id: int


class CustomerStreamingAssignmentOut(BaseModel):
    streaming_service: StreamingServiceOut
    entitlement: EntitlementLinkOut | None
    mailbox: MailboxLinkOut | None
