from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.deps.pagination import ListContext, get_list_context
from api.schemas.pagination import CursorPage
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.streaming_accounts import DbStreamingAccountRepository
from api.schemas.streaming_account import StreamingAccountCreate, StreamingAccountOut, StreamingAccountUpdate
from api.services.streaming_accounts_service import StreamingAccountsService


router = APIRouter(prefix="/streaming-accounts", tags=["streaming-accounts"])


@router.post("", response_model=StreamingAccountOut, status_code=status.HTTP_201_CREATED)
async def create_streaming_account(
    payload: StreamingAccountCreate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingAccountOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = StreamingAccountsService(DbStreamingAccountRepository(db))
            try:
                row = await service.create(entity_id=ctx.entity_id, **payload.model_dump())
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return StreamingAccountOut.model_validate(row)


@router.get("/{streaming_account_id}", response_model=StreamingAccountOut)
async def get_streaming_account(
    streaming_account_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingAccountOut:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = StreamingAccountsService(DbStreamingAccountRepository(db))
        try:
            row = await service.get(entity_id=ctx.entity_id, streaming_account_id=streaming_account_id)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    return StreamingAccountOut.model_validate(row)


@router.get("", response_model=CursorPage[StreamingAccountOut])
async def list_streaming_accounts(
    list_ctx: ListContext = Depends(get_list_context),
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CursorPage[StreamingAccountOut]:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = StreamingAccountsService(DbStreamingAccountRepository(db))
        rows, next_cursor = await service.list(
            entity_id=ctx.entity_id,
            limit=list_ctx.limit,
            after_id=list_ctx.after_id,
            q=list_ctx.q,
        )
    return CursorPage(
        items=[StreamingAccountOut.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.patch("/{streaming_account_id}", response_model=StreamingAccountOut)
async def update_streaming_account(
    streaming_account_id: int,
    payload: StreamingAccountUpdate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingAccountOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = StreamingAccountsService(DbStreamingAccountRepository(db))
            try:
                row = await service.update(
                    entity_id=ctx.entity_id,
                    streaming_account_id=streaming_account_id,
                    **payload.model_dump(),
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return StreamingAccountOut.model_validate(row)


@router.delete("/{streaming_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_streaming_account(
    streaming_account_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = StreamingAccountsService(DbStreamingAccountRepository(db))
            try:
                await service.soft_delete(entity_id=ctx.entity_id, streaming_account_id=streaming_account_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
