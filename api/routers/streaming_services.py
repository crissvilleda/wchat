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
from api.repositories.streaming_services import DbStreamingServiceRepository
from api.schemas.streaming_service import StreamingServiceCreate, StreamingServiceOut, StreamingServiceUpdate
from api.services.streaming_services_service import StreamingServicesService


router = APIRouter(prefix="/streaming-services", tags=["streaming-services"])


@router.post("", response_model=StreamingServiceOut, status_code=status.HTTP_201_CREATED)
async def create_streaming_service(
    payload: StreamingServiceCreate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingServiceOut:
    async with session_maker() as db:
        async with db.begin():
            await resolve_tenant_context_http(db, st_session)
            service = StreamingServicesService(DbStreamingServiceRepository(db))
            try:
                row = await service.create(**payload.model_dump())
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return StreamingServiceOut.model_validate(row)


@router.get("/{service_id}", response_model=StreamingServiceOut)
async def get_streaming_service(
    service_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingServiceOut:
    async with session_maker() as db:
        await resolve_tenant_context_http(db, st_session)
        service = StreamingServicesService(DbStreamingServiceRepository(db))
        try:
            row = await service.get(service_id=service_id)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    return StreamingServiceOut.model_validate(row)


@router.get("", response_model=CursorPage[StreamingServiceOut])
async def list_streaming_services(
    list_ctx: ListContext = Depends(get_list_context),
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CursorPage[StreamingServiceOut]:
    async with session_maker() as db:
        await resolve_tenant_context_http(db, st_session)
        service = StreamingServicesService(DbStreamingServiceRepository(db))
        rows, next_cursor = await service.list(
            limit=list_ctx.limit,
            after_id=list_ctx.after_id,
            q=list_ctx.q,
        )
    return CursorPage(
        items=[StreamingServiceOut.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.patch("/{service_id}", response_model=StreamingServiceOut)
async def update_streaming_service(
    service_id: int,
    payload: StreamingServiceUpdate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> StreamingServiceOut:
    async with session_maker() as db:
        async with db.begin():
            await resolve_tenant_context_http(db, st_session)
            service = StreamingServicesService(DbStreamingServiceRepository(db))
            try:
                row = await service.update(service_id=service_id, **payload.model_dump())
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return StreamingServiceOut.model_validate(row)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_streaming_service(
    service_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            await resolve_tenant_context_http(db, st_session)
            service = StreamingServicesService(DbStreamingServiceRepository(db))
            try:
                await service.soft_delete(service_id=service_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
