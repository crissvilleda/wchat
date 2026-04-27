from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator


class CustomerStreamingEntitlementAssignmentIn(BaseModel):
    streaming_service_id: int
    mailbox_id: int


class CustomerStreamingEntitlementsSync(BaseModel):
    assignments: list[CustomerStreamingEntitlementAssignmentIn]

    @model_validator(mode="after")
    def unique_streaming_services(self) -> Self:
        ids = [a.streaming_service_id for a in self.assignments]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate streaming_service_id in assignments")
        return self
