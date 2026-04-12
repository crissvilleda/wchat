"""HTTP proxy for Twilio-shaped POSTs to a configurable downstream URL.

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
from urllib.parse import unquote

import aiohttp
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

_DEFAULT_TIMEOUT_S = 30.0
_ENV_TIMEOUT = "DOWNSTREAM_TIMEOUT_SECONDS"
# When truthy, disables TLS certificate verification for downstream HTTPS (self-signed / dev only).
_ENV_INSECURE_SSL = "DOWNSTREAM_INSECURE_SSL"


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _downstream_connector() -> aiohttp.TCPConnector | None:
    if not _env_truthy(_ENV_INSECURE_SSL):
        return None
    logging.warning(
        "%s is set: downstream HTTPS certificate verification is disabled (use only for testing)",
        _ENV_INSECURE_SSL,
    )
    return aiohttp.TCPConnector(ssl=False)


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
    methods=["GET", "POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def redirect_msgs(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        return func.HttpResponse("ok", status_code=200, mimetype="text/plain")

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

    try:
        async with aiohttp.ClientSession(**session_kwargs) as session:
            async with session.post(redirect_to, data=body, headers=headers) as resp:
                downstream_body = await resp.read()
                out_ct = resp.headers.get("Content-Type", "application/octet-stream")

                if 200 <= resp.status < 300:
                    return func.HttpResponse(
                        body=downstream_body,
                        status_code=resp.status,
                        mimetype=out_ct,
                    )

                logging.warning(
                    "Downstream returned non-success status %s for redirect_to",
                    resp.status,
                )
                return func.HttpResponse(
                    "Bad Gateway",
                    status_code=502,
                    mimetype="text/plain",
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logging.exception("Downstream request failed: %s", exc)
        return func.HttpResponse(
            "Bad Gateway",
            status_code=502,
            mimetype="text/plain",
        )


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
