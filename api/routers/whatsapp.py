import logging
import os
from typing import Annotated, Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import gmail_utils
from api.deps.db import get_session_maker
from thread_utils import run_in_thread
from api.services.otp_mailbox import (
    find_mailbox_for_customer_service,
    gmail_search_query_for_service,
    list_active_streaming_services,
    match_streaming_service,
    normalize_whatsapp_sender,
)
from orm_models.mailbox_provider import MailboxProvider
from schemas import MessageSchema


router = APIRouter(prefix="/whatsapp")

# Fallback when the catalog is empty or a row has no DB-backed mailbox; uses env credentials only.
SERVICES: dict[str, str] = {
    "netflix": 'subject:Netflix "inicio de sesión"',
}

_TWILIO_ACCOUNT_SID_ENV = "TWILIO_ACCOUNT_SID"
_TWILIO_AUTH_TOKEN_ENV = "TWILIO_AUTH_TOKEN"


async def get_whatsapp_body(request: Request) -> dict[str, Any]:
    ct = (request.headers.get("content-type") or "").lower()

    if "application/json" in ct:
        json_body = await request.json()
        if isinstance(json_body, dict):
            return json_body
        if isinstance(json_body, list):
            return {"items": json_body}
        return {}

    raw = (await request.body()) or b""
    try:
        raw_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = raw.decode("utf-8", errors="replace")

    parsed = parse_qs(raw_text)
    body: dict[str, Any] = {}
    for key, value in parsed.items():
        body[key] = value[0] if len(value) == 1 else value
    return body


async def get_whatsapp_message(
    body: Annotated[dict[str, Any], Depends(get_whatsapp_body)],
) -> MessageSchema:
    return MessageSchema.model_validate(body)


WhatsappBody = Annotated[dict[str, Any], Depends(get_whatsapp_body)]
WhatsappMessage = Annotated[MessageSchema, Depends(get_whatsapp_message)]


@router.post("/webhook", status_code=200)
async def whatsapp_webhook(
    message: WhatsappMessage,
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> Response:
    from twilio.http.async_http_client import AsyncTwilioHttpClient
    from twilio.rest import Client

    client_number = message.from_
    logging.info(
        "whatsapp_webhook from=%s wa_id=%s type=%s body=%r",
        client_number,
        message.wa_id,
        message.message_type,
        message.body,
    )

    user_text = (message.body or "").strip().lower()
    logging.info(
        "whatsapp_webhook user_text=%r",
        user_text,
    )

    e164 = normalize_whatsapp_sender(client_number)
    matched_label: str | None = None
    query: str | None = None
    cred_payload: dict | None = None
    use_mailbox = False
    provider_not_supported: str | None = None
    picked = None
    services: list = []

    async with session_maker() as db:
        services = list(await list_active_streaming_services(db))
        picked = match_streaming_service(user_text, services)
        if picked is not None:
            matched_label = picked.slug
            query = gmail_search_query_for_service(picked)
            found = await find_mailbox_for_customer_service(
                db,
                whatsapp_e164=e164,
                streaming_service_id=picked.id,
            )
            if found is not None:
                mb, _cust = found
                use_mailbox = True
                if mb.provider == MailboxProvider.GMAIL.value:
                    cred_payload = mb.credential_payload
                else:
                    provider_not_supported = mb.provider
                    logging.warning(
                        "whatsapp_webhook: mailbox id=%s provider=%s not supported for Gmail OTP",
                        mb.id,
                        mb.provider,
                    )

    if matched_label is None:
        for key in SERVICES:
            if key in user_text:
                matched_label = key
                query = SERVICES[key]
                break

    if provider_not_supported:
        name = (
            picked.display_name
            if picked is not None
            else (matched_label.capitalize() if matched_label else "servicio")
        )
        output = (
            f"La cuenta {name} usa un proveedor de correo ({provider_not_supported}) que aún no está soportado."
        )
    elif matched_label and query:
        if use_mailbox and cred_payload is not None:
            otp = await run_in_thread(
                gmail_utils.get_latest_otp, query, credential_payload=cred_payload
            )
        else:
            otp = await run_in_thread(gmail_utils.get_latest_otp, query)
        logging.info("whatsapp_webhook otp_found=%s", bool(otp))
        service_title = (
            picked.display_name
            if picked is not None
            else (matched_label.capitalize() if matched_label else "servicio")
        )
        output: str | None = (
            f"Tu token de {service_title} es: *{otp}*"
            if otp
            else f"No encontré un token reciente para {service_title} en el correo."
        )
    else:
        options = "\n".join(f"• {name.capitalize()}" for name in SERVICES)
        if services:
            options = "\n".join(f"• {s.display_name}" for s in services)
        output = f"Hola 👋 ¿Para cuál cuenta necesitas el token?\n{options}"

    logging.info("whatsapp_webhook sending reply=%r to=%s", output, message.from_)
    if output:
        account_sid = os.environ.get(_TWILIO_ACCOUNT_SID_ENV)
        auth_token = os.environ.get(_TWILIO_AUTH_TOKEN_ENV)
        if not account_sid or not auth_token:
            logging.warning(
                "whatsapp_webhook: missing Twilio env vars %s=%r %s=%r; skipping reply send",
                _TWILIO_ACCOUNT_SID_ENV,
                account_sid,
                _TWILIO_AUTH_TOKEN_ENV,
                auth_token,
            )
            return Response(status_code=200)

        http_client = AsyncTwilioHttpClient()
        twilio_client = Client(account_sid, auth_token, http_client=http_client)
        await twilio_client.messages.create_async(
            body=output,
            from_=message.to,
            to=message.from_,
        )
        logging.info("whatsapp_webhook reply sent ok")

    return Response(status_code=200)
