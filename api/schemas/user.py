from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from api.schemas.common import AuditedOut


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    supertokens_user_id: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None


class UserOut(AuditedOut):
    entity_id: int
    name: str
    email: str
    supertokens_user_id: str

