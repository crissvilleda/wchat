from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.users import DbUserRepository
from api.schemas.user import UserCreate, UserOut, UserUpdate
from api.services.users_service import UsersService


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> UserOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = UsersService(DbUserRepository(db))
            try:
                user = await service.create(entity_id=ctx.entity_id, **payload.model_dump())
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> UserOut:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = UsersService(DbUserRepository(db))
        try:
            user = await service.get(entity_id=ctx.entity_id, user_id=user_id)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
async def list_users(
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserOut]:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = UsersService(DbUserRepository(db))
        users = await service.list(entity_id=ctx.entity_id, limit=limit, offset=offset)
    return [UserOut.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> UserOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = UsersService(DbUserRepository(db))
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
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = UsersService(DbUserRepository(db))
            try:
                await service.soft_delete(entity_id=ctx.entity_id, user_id=user_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
