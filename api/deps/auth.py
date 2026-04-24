from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.db import get_db_session
from api.repositories.errors import NotFoundError
from orm_models.user import User


@dataclass(frozen=True)
class TenantContext:
    user_id: int
    entity_id: int
    supertokens_user_id: str


async def get_tenant_context(
    session_: SessionContainer = Depends(verify_session()),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
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


async def get_tenant_context_http(
    session_: SessionContainer = Depends(verify_session()),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    try:
        return await get_tenant_context(session_=session_, db=db)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

