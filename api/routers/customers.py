from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import TenantContext, get_tenant_context_http
from api.deps.db import get_db_session
from api.repositories.customers import DbCustomerRepository
from api.repositories.errors import ConflictError, NotFoundError
from api.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from api.services.customers_service import CustomersService


router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> CustomerOut:
    service = CustomersService(DbCustomerRepository(db))
    try:
        customer = await service.create(entity_id=ctx.entity_id, **payload.model_dump())
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> CustomerOut:
    service = CustomersService(DbCustomerRepository(db))
    try:
        customer = await service.get(entity_id=ctx.entity_id, customer_id=customer_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CustomerOut]:
    service = CustomersService(DbCustomerRepository(db))
    customers = await service.list(entity_id=ctx.entity_id, limit=limit, offset=offset)
    return [CustomerOut.model_validate(c) for c in customers]


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> CustomerOut:
    service = CustomersService(DbCustomerRepository(db))
    try:
        customer = await service.update(entity_id=ctx.entity_id, customer_id=customer_id, **payload.model_dump())
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return CustomerOut.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    ctx: TenantContext = Depends(get_tenant_context_http),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = CustomersService(DbCustomerRepository(db))
    try:
        await service.soft_delete(entity_id=ctx.entity_id, customer_id=customer_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

