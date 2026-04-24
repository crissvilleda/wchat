from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session import SessionContainer

from api.repositories.errors import NotFoundError
from orm_models.user import User


@dataclass(frozen=True)
class TenantContext:
    user_id: int
    entity_id: int
    supertokens_user_id: str


async def resolve_tenant_context(db: AsyncSession, session_: SessionContainer) -> TenantContext:
    supertokens_user_id = session_.get_user_id()

    stmt = select(User).where(
        User.supertokens_user_id == supertokens_user_id,
        User.deleted_at.is_(None),
    )
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        raise NotFoundError("No local user linked to this session")

    return TenantContext(
        user_id=user.id,
        entity_id=user.entity_id,
        supertokens_user_id=supertokens_user_id,
    )


async def resolve_tenant_context_http(db: AsyncSession, session_: SessionContainer) -> TenantContext:
    try:
        return await resolve_tenant_context(db, session_)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
