from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from api.schemas.common import AuditedOut

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class CustomerStreamingServiceItem(BaseModel):
    slug: str
    display_name: str


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    whatsapp_e164: str = Field(min_length=8, max_length=32)

    @field_validator("whatsapp_e164")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("whatsapp_e164 must be E.164 format like +15551234567")
        return v


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    whatsapp_e164: str | None = Field(default=None, min_length=8, max_length=32)

    @field_validator("whatsapp_e164")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _E164_RE.match(v):
            raise ValueError("whatsapp_e164 must be E.164 format like +15551234567")
        return v


class CustomerOut(AuditedOut):
    entity_id: int
    name: str
    whatsapp_e164: str
    streaming_services: list[CustomerStreamingServiceItem] = Field(default_factory=list)

