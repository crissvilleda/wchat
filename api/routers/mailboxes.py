from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.deps.pagination import ListContext, get_list_context
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.mailboxes import DbMailboxRepository
from api.schemas.mailbox import MailboxCreate, MailboxOut, MailboxUpdate
from api.schemas.pagination import CursorPage
from api.services.mailboxes_service import MailboxesService
from orm_models.mailbox import Mailbox


async def _mailbox_out(svc: MailboxesService, row: Mailbox) -> MailboxOut:
    n = await svc.count_customer_links(mailbox_id=row.id)
    return MailboxOut.model_validate(row).model_copy(
        update={"current_customer_link_count": n}
    )


router = APIRouter(prefix="/mailboxes", tags=["mailboxes"])


@router.post("", response_model=MailboxOut, status_code=status.HTTP_201_CREATED)
async def create_mailbox(
    payload: MailboxCreate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> MailboxOut:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            svc = MailboxesService(DbMailboxRepository(db))
            try:
                row = await svc.create(
                    entity_id=ctx.entity_id,
                    **payload.model_dump(),
                )
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
    # New mailbox has 0 customer links; avoid extra round trip.
    return MailboxOut.model_validate(row)


@router.get("/{mailbox_id}", response_model=MailboxOut)
async def get_mailbox(
    mailbox_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> MailboxOut:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        svc = MailboxesService(DbMailboxRepository(db))
        try:
            row = await svc.get(entity_id=ctx.entity_id, mailbox_id=mailbox_id)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return await _mailbox_out(svc, row)


@router.get("", response_model=CursorPage[MailboxOut])
async def list_mailboxes(
    list_ctx: ListContext = Depends(get_list_context),
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> CursorPage[MailboxOut]:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        svc = MailboxesService(DbMailboxRepository(db))
        rows, next_c = await svc.list(
            entity_id=ctx.entity_id,
            limit=list_ctx.limit,
            after_id=list_ctx.after_id,
            q=list_ctx.q,
        )
        items = [await _mailbox_out(svc, r) for r in rows]
    return CursorPage(items=items, next_cursor=next_c)


@router.patch("/{mailbox_id}", response_model=MailboxOut)
async def update_mailbox(
    mailbox_id: int,
    payload: MailboxUpdate,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> MailboxOut:
    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)
        svc = MailboxesService(DbMailboxRepository(db))
        async with db.begin():
            d = payload.model_dump(exclude_unset=True)
            if not d:
                try:
                    row = await svc.get(entity_id=ctx.entity_id, mailbox_id=mailbox_id)
                except NotFoundError as e:
                    raise HTTPException(status_code=404, detail=str(e)) from e
            else:
                try:
                    row = await svc.update(
                        entity_id=ctx.entity_id,
                        mailbox_id=mailbox_id,
                        **d,
                    )
                except NotFoundError as e:
                    raise HTTPException(status_code=404, detail=str(e)) from e
                except ConflictError as e:
                    raise HTTPException(status_code=409, detail=str(e)) from e
        return await _mailbox_out(svc, row)


@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailbox(
    mailbox_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            svc = MailboxesService(DbMailboxRepository(db))
            try:
                await svc.soft_delete(entity_id=ctx.entity_id, mailbox_id=mailbox_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/{mailbox_id}/customer-links/{customer_id}",
    status_code=status.HTTP_201_CREATED,
)
async def link_customer_to_mailbox(
    mailbox_id: int,
    customer_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            svc = MailboxesService(DbMailboxRepository(db))
            try:
                await svc.link_customer(
                    entity_id=ctx.entity_id,
                    mailbox_id=mailbox_id,
                    customer_id=customer_id,
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e


@router.delete(
    "/{mailbox_id}/customer-links/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_customer_from_mailbox(
    mailbox_id: int,
    customer_id: int,
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> None:
    async with session_maker() as db:
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            svc = MailboxesService(DbMailboxRepository(db))
            try:
                await svc.unlink_customer(
                    entity_id=ctx.entity_id,
                    mailbox_id=mailbox_id,
                    customer_id=customer_id,
                )
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
