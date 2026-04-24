from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import TenantContext, get_tenant_context_http
from api.deps.db import get_db_session
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.users import SqlAlchemyUserRepository
from api.schemas.user import UserCreate, UserOut, UserUpdate
from api.services.users_service import UsersService


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    service = UsersService(SqlAlchemyUserRepository(db))
    try:
        user = await service.create(entity_id=ctx.entity_id, **payload.model_dump())
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    service = UsersService(SqlAlchemyUserRepository(db))
    try:
        user = await service.get(entity_id=ctx.entity_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
async def list_users(
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserOut]:
    service = UsersService(SqlAlchemyUserRepository(db))
    users = await service.list(entity_id=ctx.entity_id, limit=limit, offset=offset)
    return [UserOut.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    service = UsersService(SqlAlchemyUserRepository(db))
    try:
        user = await service.update(entity_id=ctx.entity_id, user_id=user_id, **payload.model_dump())
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = UsersService(SqlAlchemyUserRepository(db))
    try:
        await service.soft_delete(entity_id=ctx.entity_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

