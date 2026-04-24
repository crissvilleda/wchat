from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import TenantContext, get_tenant_context_http
from api.deps.db import get_db_session
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.streaming_services import DbStreamingServiceRepository
from api.schemas.streaming_service import StreamingServiceCreate, StreamingServiceOut, StreamingServiceUpdate
from api.services.streaming_services_service import StreamingServicesService


router = APIRouter(prefix="/streaming-services", tags=["streaming-services"])


@router.post("", response_model=StreamingServiceOut, status_code=status.HTTP_201_CREATED)
async def create_streaming_service(
    payload: StreamingServiceCreate,
    _: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingServiceOut:
    service = StreamingServicesService(DbStreamingServiceRepository(db))
    try:
        row = await service.create(**payload.model_dump())
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return StreamingServiceOut.model_validate(row)


@router.get("/{service_id}", response_model=StreamingServiceOut)
async def get_streaming_service(
    service_id: int,
    _: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingServiceOut:
    service = StreamingServicesService(DbStreamingServiceRepository(db))
    try:
        row = await service.get(service_id=service_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return StreamingServiceOut.model_validate(row)


@router.get("", response_model=list[StreamingServiceOut])
async def list_streaming_services(
    _: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[StreamingServiceOut]:
    service = StreamingServicesService(DbStreamingServiceRepository(db))
    rows = await service.list(limit=limit, offset=offset)
    return [StreamingServiceOut.model_validate(r) for r in rows]


@router.patch("/{service_id}", response_model=StreamingServiceOut)
async def update_streaming_service(
    service_id: int,
    payload: StreamingServiceUpdate,
    _: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingServiceOut:
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
    _: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = StreamingServicesService(DbStreamingServiceRepository(db))
    try:
        await service.soft_delete(service_id=service_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

