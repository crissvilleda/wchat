from __future__ import annotations

from api.schemas.common import AuditedOut


class CustomerStreamingEntitlementOut(AuditedOut):
    customer_id: int
    streaming_service_id: int
    mailbox_id: int | None
