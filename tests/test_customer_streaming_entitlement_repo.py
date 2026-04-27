from __future__ import annotations

from datetime import datetime, timezone

import pytest
import orm_models  # noqa: F401 — register models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.repositories.customer_streaming_entitlements import (
    DbCustomerStreamingEntitlementRepository,
)
from orm_models.base import BaseModel
from orm_models.customer import Customer
from orm_models.customer_mailbox import CustomerMailbox
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement
from orm_models.entity import Entity
from orm_models.mailbox import Mailbox
from orm_models.streaming_service import StreamingService


@pytest.mark.asyncio
async def test_upsert_revives_soft_deleted_entitlement_instead_of_insert():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    entity_id: int
    customer_id: int
    mailbox_id: int
    service_id: int

    async with session_maker() as session:
        ent_row = Entity(name="Tenant")
        session.add(ent_row)
        await session.flush()
        entity_id = ent_row.id
        cust = Customer(
            entity_id=entity_id, name="Maria", whatsapp_e164="+5033459340343"
        )
        mb = Mailbox(
            entity_id=entity_id,
            mailbox_address="poll@gmail.com",
            provider="gmail",
        )
        svc = StreamingService(slug="netflix", display_name="Netflix")
        session.add_all([cust, mb, svc])
        await session.flush()
        customer_id = cust.id
        mailbox_id = mb.id
        service_id = svc.id
        session.add(CustomerMailbox(customer_id=customer_id, mailbox_id=mailbox_id))
        session.add(
            CustomerStreamingEntitlement(
                customer_id=customer_id,
                streaming_service_id=service_id,
                mailbox_id=mailbox_id,
            )
        )
        await session.commit()

    async with session_maker() as session:
        stmt = select(CustomerStreamingEntitlement).where(
            CustomerStreamingEntitlement.customer_id == customer_id,
            CustomerStreamingEntitlement.streaming_service_id == service_id,
        )
        row = (await session.execute(stmt)).scalars().first()
        assert row is not None
        row.deleted_at = datetime.now(tz=timezone.utc)
        await session.commit()

    async with session_maker() as session:
        async with session.begin():
            repo = DbCustomerStreamingEntitlementRepository(session)
            restored = await repo.upsert(
                entity_id=entity_id,
                customer_id=customer_id,
                streaming_service_id=service_id,
                mailbox_id=mailbox_id,
            )
        assert restored.deleted_at is None
        assert restored.mailbox_id == mailbox_id

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_streaming_services_for_customers():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_maker() as session:
        ent_row = Entity(name="T")
        session.add(ent_row)
        await session.flush()
        entity_id = ent_row.id
        cust = Customer(entity_id=entity_id, name="A", whatsapp_e164="+15550001111")
        mb = Mailbox(
            entity_id=entity_id,
            mailbox_address="a@gmail.com",
            provider="gmail",
        )
        svc = StreamingService(slug="hulu", display_name="Hulu")
        session.add_all([cust, mb, svc])
        await session.flush()
        session.add(CustomerMailbox(customer_id=cust.id, mailbox_id=mb.id))
        session.add(
            CustomerStreamingEntitlement(
                customer_id=cust.id,
                streaming_service_id=svc.id,
                mailbox_id=mb.id,
            )
        )
        await session.commit()
        customer_id = cust.id

    async with session_maker() as session:
        repo = DbCustomerStreamingEntitlementRepository(session)
        out = await repo.list_streaming_services_for_customers(
            entity_id=entity_id,
            customer_ids=[customer_id],
        )
    assert out[customer_id] == [("hulu", "Hulu")]

    await engine.dispose()
