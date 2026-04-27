from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orm_models.customer import Customer
from orm_models.customer_streaming_entitlement import CustomerStreamingEntitlement
from orm_models.mailbox import Mailbox
from orm_models.streaming_service import StreamingService


def normalize_whatsapp_sender(raw: str) -> str:
    s = (raw or "").strip()
    if s.lower().startswith("whatsapp:"):
        s = s[9:].strip()
    return s


def gmail_search_query_for_service(service: StreamingService) -> str:
    return f'subject:{service.display_name} "inicio de sesión"'


async def list_active_streaming_services(
    db: AsyncSession,
) -> Sequence[StreamingService]:
    stmt = (
        select(StreamingService)
        .where(StreamingService.deleted_at.is_(None))
        .order_by(StreamingService.id.asc())
    )
    return (await db.execute(stmt)).scalars().all()


def match_streaming_service(
    user_text: str, services: Sequence[StreamingService]
) -> StreamingService | None:
    t = (user_text or "").strip().lower()
    for s in services:
        if s.slug.lower() in t:
            return s
        for p in s.keyword_patterns or []:
            if p.lower() in t:
                return s
    return None


async def find_mailbox_for_customer_service(
    db: AsyncSession,
    *,
    whatsapp_e164: str,
    streaming_service_id: int,
) -> tuple[Mailbox, Customer] | None:
    stmt = (
        select(Mailbox, Customer)
        .join(
            CustomerStreamingEntitlement,
            CustomerStreamingEntitlement.mailbox_id == Mailbox.id,
        )
        .join(Customer, Customer.id == CustomerStreamingEntitlement.customer_id)
        .where(
            Customer.whatsapp_e164 == whatsapp_e164,
            Customer.deleted_at.is_(None),
            CustomerStreamingEntitlement.streaming_service_id == streaming_service_id,
            CustomerStreamingEntitlement.deleted_at.is_(None),
            CustomerStreamingEntitlement.mailbox_id.isnot(None),
            Mailbox.deleted_at.is_(None),
        )
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return None
    if len(rows) > 1:
        logging.warning(
            "otp_mailbox: multiple mailbox rows for phone=%s service_id=%s; using first",
            whatsapp_e164,
            streaming_service_id,
        )
    mb, customer = rows[0]
    return (mb, customer)
