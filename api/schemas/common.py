from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuditedOut(ORMBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

