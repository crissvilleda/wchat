from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select

from api.repositories.search import ilike_or_columns, keyset_paginate_result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.errors import ConflictError, NotFoundError
from orm_models.customer import Customer


class CustomerRepository(Protocol):
    async def create(self, *, entity_id: int, name: str, whatsapp_e164: str) -> Customer: ...
    async def get(self, *, entity_id: int, customer_id: int) -> Customer: ...
    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Customer], int | None]: ...
    async def update(
        self, *, entity_id: int, customer_id: int, name: str | None, whatsapp_e164: str | None
    ) -> Customer: ...
    async def soft_delete(self, *, entity_id: int, customer_id: int) -> None: ...


class DbCustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, entity_id: int, name: str, whatsapp_e164: str) -> Customer:
        customer = Customer(entity_id=entity_id, name=name, whatsapp_e164=whatsapp_e164)
        self._db.add(customer)
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Customer already exists") from e
        await self._db.refresh(customer)
        return customer

    async def get(self, *, entity_id: int, customer_id: int) -> Customer:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.entity_id == entity_id,
            Customer.deleted_at.is_(None),
        )
        customer = (await self._db.execute(stmt)).scalars().first()
        if not customer:
            raise NotFoundError("Customer not found")
        return customer

    async def list(
        self, *, entity_id: int, limit: int, after_id: int | None, q: str | None
    ) -> tuple[Sequence[Customer], int | None]:
        stmt = select(Customer).where(Customer.entity_id == entity_id, Customer.deleted_at.is_(None))
        if after_id is not None:
            stmt = stmt.where(Customer.id > after_id)
        if q is not None:
            stmt = stmt.where(ilike_or_columns(Customer.name, Customer.whatsapp_e164, term=q))
        stmt = stmt.order_by(Customer.id.asc()).limit(limit + 1)
        rows = (await self._db.execute(stmt)).scalars().all()
        page, next_id = keyset_paginate_result(rows, limit=limit, id_getter="id")
        return page, next_id

    async def update(
        self, *, entity_id: int, customer_id: int, name: str | None, whatsapp_e164: str | None
    ) -> Customer:
        customer = await self.get(entity_id=entity_id, customer_id=customer_id)
        if name is not None:
            customer.name = name
        if whatsapp_e164 is not None:
            customer.whatsapp_e164 = whatsapp_e164
        try:
            await self._db.flush()
        except IntegrityError as e:
            raise ConflictError("Update conflict") from e
        await self._db.refresh(customer)
        return customer

    async def soft_delete(self, *, entity_id: int, customer_id: int) -> None:
        customer = await self.get(entity_id=entity_id, customer_id=customer_id)
        customer.deleted_at = datetime.now(tz=timezone.utc)
        await self._db.flush()

