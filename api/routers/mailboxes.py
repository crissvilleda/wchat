from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import aiohttp
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

import gmail_utils
from api.deps.auth import resolve_tenant_context_http
from api.deps.db import get_session_maker
from api.deps.pagination import ListContext, get_list_context
from api.repositories.errors import ConflictError, NotFoundError
from api.repositories.mailboxes import DbMailboxRepository
from api.schemas.mailbox import MailboxCreate, MailboxOut, MailboxUpdate
from api.schemas.pagination import CursorPage
from api.services.mailboxes_service import MailboxesService
from orm_models.mailbox import Mailbox

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


async def _mailbox_out(svc: MailboxesService, row: Mailbox) -> MailboxOut:
    n = await svc.count_customer_links(mailbox_id=row.id)
    gmail_connected = (
        row.provider == "gmail"
        and bool(row.credential_payload)
        and row.revoked_at is None
    )
    return MailboxOut.model_validate(row).model_copy(
        update={"current_customer_link_count": n, "gmail_connected": gmail_connected}
    )


router = APIRouter(prefix="/mailboxes", tags=["mailboxes"])


@router.get("/gmail-auth-url")
async def get_gmail_auth_url(
    state: str = Query(..., min_length=1, max_length=256),
    st_session: SessionContainer = Depends(verify_session()),
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> dict[str, str]:
    secret = os.environ.get("OAUTH_STATE_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="OAUTH_STATE_SECRET no está configurado.")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth no está configurado en el servidor.")

    async with session_maker() as db:
        ctx = await resolve_tenant_context_http(db, st_session)

    now = datetime.now(timezone.utc)
    signed_state = jwt.encode(
        {
            "entity_id": ctx.entity_id,
            "user_id": ctx.user_id,
            "nonce": state,
            "exp": now + timedelta(minutes=10),
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": _GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": signed_state,
    }
    return {"auth_url": f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"}


@router.get("/gmail-callback")
async def gmail_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> JSONResponse:
    if error or not code or not state:
        return JSONResponse({"ok": False, "nonce": None, "error": error or "cancelled"}, status_code=400)

    secret = os.environ.get("OAUTH_STATE_SECRET", "")
    try:
        claims: dict = jwt.decode(state, secret, algorithms=["HS256"])
        entity_id: int = int(claims["entity_id"])
        nonce: str = str(claims["nonce"])
    except Exception as exc:
        logging.warning("gmail_oauth_callback: invalid state JWT: %s", exc)
        return JSONResponse({"ok": False, "nonce": None, "error": "invalid_state"}, status_code=400)

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        return JSONResponse({"ok": False, "nonce": nonce, "error": "server_misconfigured"}, status_code=500)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            ) as resp:
                token_data: dict = await resp.json(content_type=None)
    except Exception as exc:
        logging.error("gmail_oauth_callback: token exchange failed: %s", exc)
        return JSONResponse({"ok": False, "nonce": nonce, "error": "token_exchange_failed"}, status_code=502)

    if "error" in token_data:
        return JSONResponse({"ok": False, "nonce": nonce, "error": token_data.get("error", "unknown")}, status_code=400)

    access_token: str = token_data.get("access_token", "")

    mailbox_address = gmail_utils.get_profile_email(access_token)
    if not mailbox_address:
        return JSONResponse({"ok": False, "nonce": nonce, "error": "profile_fetch_failed"}, status_code=502)

    expires_in = token_data.get("expires_in")
    token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        if expires_in is not None else None
    )
    token_scopes: str | None = token_data.get("scope")
    credential = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": _GOOGLE_TOKEN_URL,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        async with session_maker() as db:
            async with db.begin():
                svc = MailboxesService(DbMailboxRepository(db))
                await svc.upsert_gmail_credentials(
                    entity_id=entity_id,
                    mailbox_address=mailbox_address,
                    credential_payload=credential,
                    token_scopes=token_scopes,
                    token_expiry=token_expiry,
                )
    except Exception as exc:
        logging.error("gmail_oauth_callback: upsert failed: %s", exc)
        return JSONResponse({"ok": False, "nonce": nonce, "error": "save_failed"}, status_code=500)

    return JSONResponse({"ok": True, "nonce": nonce, "mailbox_address": mailbox_address})


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
                    provider=payload.provider,
                    mailbox_address=payload.mailbox_address,
                    credential_payload=None,
                    secret_ref=None,
                    token_scopes=None,
                    token_expiry=None,
                    max_customer_links=payload.max_customer_links,
                )
            except ConflictError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
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
        async with db.begin():
            ctx = await resolve_tenant_context_http(db, st_session)
            svc = MailboxesService(DbMailboxRepository(db))
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
                        provider=None,
                        mailbox_address=None,
                        credential_payload=None,
                        secret_ref=None,
                        token_scopes=None,
                        token_expiry=None,
                        revoked_at=None,
                        max_customer_links=d.get("max_customer_links"),
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
