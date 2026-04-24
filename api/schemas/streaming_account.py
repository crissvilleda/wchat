from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.common import AuditedOut


class StreamingAccountCreate(BaseModel):
    streaming_service_id: int
    label: str = Field(min_length=1, max_length=255)
    is_active: bool = True


class StreamingAccountUpdate(BaseModel):
    streaming_service_id: int | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class StreamingAccountOut(AuditedOut):
    entity_id: int
    streaming_service_id: int
    label: str
    is_active: bool

