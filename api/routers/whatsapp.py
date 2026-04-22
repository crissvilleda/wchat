import asyncio
import logging
import os
from typing import Annotated, Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

import gmail_utils
from schemas import MessageSchema


router = APIRouter(prefix="/whatsapp")

# Servicios disponibles: keyword → consulta de Gmail
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
async def whatsapp_webhook(message: WhatsappMessage) -> Response:
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
        "whatsapp_webhook user_text=%r services_available=%s",
        user_text,
        list(SERVICES),
    )

    matched_service: str | None = next(
        (key for key in SERVICES if key in user_text), None)
    logging.info("whatsapp_webhook matched_service=%r", matched_service)

    if matched_service:
        query = SERVICES[matched_service]
        logging.info(
            "whatsapp_webhook fetching OTP from Gmail query=%r", query)
        otp = await asyncio.to_thread(gmail_utils.get_latest_otp, query)
        logging.info("whatsapp_webhook otp_found=%s", bool(otp))

        output: str | None = (
            f"Tu token de {matched_service.capitalize()} es: *{otp}*"
            if otp
            else f"No encontré un token reciente para {matched_service.capitalize()} en el correo."
        )
    else:
        options = "\n".join(f"• {name.capitalize()}" for name in SERVICES)
        output = f"Hola 👋 ¿Para cuál cuenta necesitas el token?\n{options}"

    logging.info("whatsapp_webhook sending reply=%r to=%s",
                 output, message.from_)
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
        twilio_client = Client(account_sid, auth_token,
                               http_client=http_client)
        await twilio_client.messages.create_async(
            body=output,
            from_=message.to,
            to=message.from_,
        )
        logging.info("whatsapp_webhook reply sent ok")

    return Response(status_code=200)
