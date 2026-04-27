from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.repositories.customer_streaming_entitlements import (
    DbCustomerStreamingEntitlementRepository,
)
from api.repositories.errors import ConflictError, NotFoundError
from api.schemas.customer_streaming_entitlement_out import CustomerStreamingEntitlementOut
from api.schemas.customer_streaming_entitlement_overview import CustomerStreamingAssignmentOut
from api.schemas.customer_streaming_entitlement_upsert import (
    CustomerStreamingEntitlementUpsert,
)
from api.services.customer_streaming_entitlements_service import (
    CustomerStreamingEntitlementsService,
)


router = APIRouter(prefix="/customers", tags=["customer-streaming-entitlements"])


@router.get(
    "/{customer_id}/streaming-entitlements",
    response_model=list[CustomerStreamingAssignmentOut],
)
async def list_customer_streaming_entitlements(
    customer_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> list[CustomerStreamingAssignmentOut]:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = CustomerStreamingEntitlementsService(
            DbCustomerStreamingEntitlementRepository(db)
        )
        try:
            return await service.list_assignments_for_customer(
                entity_id=ctx.entity_id,
                customer_id=customer_id,
            )
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e


@router.put(
    "/{customer_id}/streaming-entitlements/{streaming_service_id}",
    response_model=CustomerStreamingEntitlementOut,
)
async def upsert_customer_streaming_entitlement(
    customer_id: int,
    streaming_service_id: int,
    payload: CustomerStreamingEntitlementUpsert,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CustomerStreamingEntitlementOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = CustomerStreamingEntitlementsService(
                DbCustomerStreamingEntitlementRepository(db)
            )
            try:
                row = await service.upsert(
                    entity_id=ctx.entity_id,
                    customer_id=customer_id,
                    streaming_service_id=streaming_service_id,
                    **payload.model_dump(),
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return CustomerStreamingEntitlementOut.model_validate(row)


@router.delete(
    "/{customer_id}/streaming-entitlements/{streaming_service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer_streaming_entitlement(
    customer_id: int,
    streaming_service_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = CustomerStreamingEntitlementsService(
                DbCustomerStreamingEntitlementRepository(db)
            )
            try:
                await service.soft_delete(
                    entity_id=ctx.entity_id,
                    customer_id=customer_id,
                    streaming_service_id=streaming_service_id,
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
