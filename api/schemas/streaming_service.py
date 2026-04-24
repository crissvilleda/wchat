from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from api.schemas.common import AuditedOut

_SLUG_RE = re.compile(r"^[a-z0-9_\\-]{2,64}$")


class StreamingServiceCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=255)
    keyword_patterns: list[str] | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("slug must match ^[a-z0-9_\\-]{2,64}$")
        return v


class StreamingServiceUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    keyword_patterns: list[str] | None = None


class StreamingServiceOut(AuditedOut):
    slug: str
    display_name: str
    keyword_patterns: list[str] | None

