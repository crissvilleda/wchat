"""HTTP proxy for Twilio-shaped POST or PATCH requests to a configurable downstream URL.

Webhook URL for Twilio should include the function key, e.g.
``.../redirect_msgs?code=<FUNCTION_KEY>&redirect_to=<encoded downstream URL>``,
because this route uses ``AuthLevel.FUNCTION``. Switching to ``ANONYMOUS`` would
let anyone use the app as an open HTTP proxy—only do that in isolated tests.

Set ``DOWNSTREAM_INSECURE_SSL`` to ``1``/``true``/``yes``/``on`` only when testing
against HTTPS endpoints with self-signed certificates; it disables TLS verification
for the outbound aiohttp client.
"""

import asyncio
import json
import logging
import os
import ssl
from urllib.parse import unquote

import aiohttp
import azure.functions as func

from request_utils import get_body_from_request
from schemas import MessageSchema

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

_DEFAULT_TIMEOUT_S = 30.0
_ENV_TIMEOUT = "DOWNSTREAM_TIMEOUT_SECONDS"
# When truthy, disables TLS certificate verification for downstream HTTPS (self-signed / dev only).
_ENV_INSECURE_SSL = "DOWNSTREAM_INSECURE_SSL"


def _get_app_setting(name: str) -> str | None:
    """Read env var; on Azure App Service / Functions the same value may appear with an ``APPSETTING_`` prefix."""
    raw = os.environ.get(name)
    if raw is not None and raw.strip() != "":
        return raw
    prefixed = os.environ.get(f"APPSETTING_{name}")
    if prefixed is not None and prefixed.strip() != "":
        return prefixed
    return None


def _env_truthy(name: str) -> bool:
    raw = _get_app_setting(name)
    if raw is None:
        return False
    raw = raw.strip().strip('"').strip("'")
    if raw == "":
        return False
    return raw.lower() in ("1", "true", "yes", "on")


def _unverified_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _downstream_connector() -> aiohttp.TCPConnector | None:
    if not _env_truthy(_ENV_INSECURE_SSL):
        return None
    logging.warning(
        "%s is set: downstream HTTPS certificate verification is disabled (use only for testing)",
        _ENV_INSECURE_SSL,
    )
    return aiohttp.TCPConnector(ssl=_unverified_ssl_context())


def _client_timeout() -> aiohttp.ClientTimeout:
    raw = os.environ.get(_ENV_TIMEOUT)
    if raw is None or raw.strip() == "":
        total = _DEFAULT_TIMEOUT_S
    else:
        try:
            total = float(raw)
        except ValueError:
            total = _DEFAULT_TIMEOUT_S
    return aiohttp.ClientTimeout(total=total)


@app.route(
    route="redirect_msgs",
    methods=["POST", "PATCH"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def redirect_msgs(req: func.HttpRequest) -> func.HttpResponse:
    method = req.method.upper()
    if method not in ("POST", "PATCH"):
        return func.HttpResponse(
            "Method Not Allowed",
            status_code=405,
            mimetype="text/plain",
        )


    ## Obtener cliente
        ## Buscar por numero o buscar por id

    ## Obtener cuentas del cliente
        ## Enviar plantilla de whatsapp con opciones
        
    ## Obtener token del ultimo correo de la cuenta
        ## Buscar en gmail
        ## Obtener el token de la cuenta selecionada


    ## Responde con el token al usuario


    

    redirect_to = req.params.get("redirect_to")
    if not redirect_to or not redirect_to.strip():
        return func.HttpResponse(
            "Missing required query parameter: redirect_to",
            status_code=400,
            mimetype="text/plain",
        )

    redirect_to = unquote(redirect_to.strip())
    body = req.get_body() or b""
    content_type = req.headers.get("Content-Type")
    if not content_type:
        content_type = "application/x-www-form-urlencoded"

    headers = {"Content-Type": content_type}
    timeout = _client_timeout()
    connector = _downstream_connector()
    session_kwargs = {"timeout": timeout}
    if connector is not None:
        session_kwargs["connector"] = connector

    logging.info(
        "redirect_msgs method=%s redirect_to=%r downstream TLS verify=%s %s=%r",
        method,
        redirect_to,
        "off" if connector is not None else "on",
        _ENV_INSECURE_SSL,
        _get_app_setting(_ENV_INSECURE_SSL),
    )

    try:
        async with aiohttp.ClientSession(**session_kwargs) as session:
            async with session.request(method, redirect_to, data=body, headers=headers) as resp:
                downstream_body = await resp.read()
                out_ct = resp.headers.get("Content-Type", "application/octet-stream")

                if 200 <= resp.status < 300:
                    return func.HttpResponse(
                        body=downstream_body,
                        status_code=resp.status,
                        mimetype=out_ct,
                    )

                logging.warning(
                    "Downstream returned non-success status %s redirect_to=%r",
                    resp.status,
                    redirect_to,
                )
                return func.HttpResponse(
                    "Bad Gateway",
                    status_code=502,
                    mimetype="text/plain",
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logging.exception(
            "Downstream request failed redirect_to=%r: %s",
            redirect_to,
            exc,
        )
        return func.HttpResponse(
            "Bad Gateway",
            status_code=502,
            mimetype="text/plain",
        )


@app.route(
    route="whatsapp/webhook",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def whatsapp_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """Receive incoming Twilio WhatsApp webhook, parse it, and send a reply.

    Twilio POSTs ``application/x-www-form-urlencoded`` form data.  We parse it
    into a ``MessageSchema`` and then use the Twilio async client to respond.

    Environment variables required:
        TWILIO_ACCOUNT_SID  – Twilio account SID
        TWILIO_AUTH_TOKEN   – Twilio auth token
    """
    from twilio.rest import Client
    from twilio.http.async_http_client import AsyncTwilioHttpClient

    body = get_body_from_request(req)
    message = MessageSchema(**body)

    logging.info(
        "whatsapp_webhook wa_id=%s from=%s type=%s",
        message.wa_id,
        message.from_,
        message.message_type,
    )

    # --- Build your reply here ---
    # Replace this stub with whatever response logic you need.
    output: str | None = "Test 123"  # set to the text you want to send back

    if output:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        http_client = AsyncTwilioHttpClient()
        twilio_client = Client(account_sid, auth_token, http_client=http_client)
        await twilio_client.messages.create_async(
            body=output,
            from_=message.to,
            to=message.from_,
        )

    # Twilio expects a 200 to acknowledge receipt of the webhook.
    return func.HttpResponse(status_code=200)


@app.route(
    route="dummy_redirect_echo",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def dummy_redirect_echo(req: func.HttpRequest) -> func.HttpResponse:
    """Local/test sink: accepts POST only. Use as ``redirect_to`` to verify the proxy.

    Example (func host): ``http://localhost:7071/api/dummy_redirect_echo?code=...``
    """

    raw = req.get_body() or b""
    ct = req.headers.get("Content-Type") or "application/octet-stream"
    try:
        body_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        body_text = raw.decode("utf-8", errors="replace")

    payload = {
        "ok": True,
        "content_type": ct,
        "body_length": len(raw),
        "body": body_text,
    }
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        status_code=200,
        mimetype="application/json; charset=utf-8",
    )
