from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.deps.pagination import ListContext, get_list_context
from api.schemas.pagination import CursorPage
from api.repositories.customer_streaming_entitlements import (
    DbCustomerStreamingEntitlementRepository,
)
from api.repositories.customers import DbCustomerRepository
from api.repositories.errors import ConflictError, NotFoundError
from api.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from api.services.customers_service import CustomersService


router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CustomerOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = CustomersService(DbCustomerRepository(db))
            try:
                customer = await service.create(entity_id=ctx.entity_id, **payload.model_dump())
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CustomerOut:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = CustomersService(DbCustomerRepository(db))
        try:
            customer = await service.get(entity_id=ctx.entity_id, customer_id=customer_id)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.get("", response_model=CursorPage[CustomerOut])
async def list_customers(
    list_ctx: ListContext = Depends(get_list_context),
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CursorPage[CustomerOut]:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        service = CustomersService(DbCustomerRepository(db))
        ent_repo = DbCustomerStreamingEntitlementRepository(db)
        customers, next_cursor = await service.list(
            entity_id=ctx.entity_id,
            limit=list_ctx.limit,
            after_id=list_ctx.after_id,
            q=list_ctx.q,
        )
        customer_ids = [c.id for c in customers]
        slugs_by_customer = await ent_repo.list_streaming_service_slugs_for_customers(
            entity_id=ctx.entity_id,
            customer_ids=customer_ids,
        )
    return CursorPage(
        items=[
            CustomerOut.model_validate(c).model_copy(
                update={"streaming_service_slugs": slugs_by_customer.get(c.id, [])}
            )
            for c in customers
        ],
        next_cursor=next_cursor,
    )


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CustomerOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = CustomersService(DbCustomerRepository(db))
            try:
                customer = await service.update(
                    entity_id=ctx.entity_id, customer_id=customer_id, **payload.model_dump()
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            service = CustomersService(DbCustomerRepository(db))
            try:
                await service.soft_delete(entity_id=ctx.entity_id, customer_id=customer_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
