from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import gmail_utils
import twilio.http.async_http_client
import twilio.rest
import api.routers.whatsapp as _whatsapp_router
from api import fastapi_app
from api.deps.db import get_session_maker
from orm_models.mailbox_provider import MailboxProvider

_FORM = {
    "MessageSid": "SM123",
    "NumMedia": "0",
    "MessageType": "text",
    "WaId": "15551231234",
    "SmsStatus": "received",
    "To": "whatsapp:+15550001111",
    "From": "whatsapp:+15551231234",
    "Body": "netflix",
}


class _FakeMessages:
    def __init__(self):
        self.calls = []

    async def create_async(self, *, body: str, from_: str, to: str):
        self.calls.append({"body": body, "from_": from_, "to": to})


class _FakeTwilioClient:
    def __init__(self, *args, **kwargs):
        self.messages = _FakeMessages()


class _FakeAsyncTwilioHttpClient:
    pass


class _MockSession:
    """Async context manager that yields a plain MagicMock as the DB session."""
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *_):
        return False


def _mock_session_maker():
    return _MockSession()


@pytest.fixture
async def webhook_client(monkeypatch):
    # Override DB dependency — no real connection is ever made.
    fastapi_app.dependency_overrides[get_session_maker] = lambda: _mock_session_maker

    # Default: empty service catalog, no mailbox found.
    monkeypatch.setattr(_whatsapp_router, "list_active_streaming_services", AsyncMock(return_value=[]))
    monkeypatch.setattr(_whatsapp_router, "find_mailbox_for_customer_service", AsyncMock(return_value=None))

    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")

    otp_calls: list[dict] = []
    otp_box: dict = {"return_value": "123456"}

    def fake_otp(query, *, credential_payload=None):
        otp_calls.append({"query": query, "credential_payload": credential_payload})
        return otp_box["return_value"]

    monkeypatch.setattr(gmail_utils, "get_latest_otp", fake_otp)
    monkeypatch.setattr(twilio.http.async_http_client, "AsyncTwilioHttpClient", _FakeAsyncTwilioHttpClient)

    fake_twilio = _FakeTwilioClient()
    monkeypatch.setattr(twilio.rest, "Client", lambda *a, **k: fake_twilio)

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        yield client, fake_twilio, otp_calls, otp_box

    fastapi_app.dependency_overrides.pop(get_session_maker, None)


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_twilio_form_and_replies(webhook_client):
    client, fake_twilio, otp_calls, otp_box = webhook_client

    resp = await client.post("/api/whatsapp/webhook", data=_FORM)

    assert resp.status_code == 200
    assert fake_twilio.messages.calls, "Expected a Twilio reply to be sent"
    sent = fake_twilio.messages.calls[0]
    assert sent["to"] == "whatsapp:+15551231234"
    assert sent["from_"] == "whatsapp:+15550001111"
    assert "123456" in sent["body"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_no_otp_found(webhook_client):
    client, fake_twilio, otp_calls, otp_box = webhook_client
    otp_box["return_value"] = None

    resp = await client.post("/api/whatsapp/webhook", data=_FORM)

    assert resp.status_code == 200
    assert len(otp_calls) == 1
    sent = fake_twilio.messages.calls[0]
    assert "No encontré un token reciente" in sent["body"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_unknown_service_returns_options(webhook_client):
    client, fake_twilio, otp_calls, otp_box = webhook_client

    resp = await client.post("/api/whatsapp/webhook", data={**_FORM, "Body": "ayuda"})

    assert resp.status_code == 200
    assert otp_calls == [], "OTP must not be attempted for an unrecognized service"
    sent = fake_twilio.messages.calls[0]
    assert sent["body"].startswith("Hola 👋")
    assert "Netflix" in sent["body"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_missing_twilio_credentials_returns_200(webhook_client, monkeypatch):
    client, fake_twilio, otp_calls, otp_box = webhook_client
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    otp_box["return_value"] = "999999"

    resp = await client.post("/api/whatsapp/webhook", data=_FORM)

    assert resp.status_code == 200
    assert fake_twilio.messages.calls == [], "Twilio must not be called when credentials are absent"
    assert len(otp_calls) == 1


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_json_body(webhook_client):
    client, fake_twilio, otp_calls, otp_box = webhook_client
    otp_box["return_value"] = "654321"

    resp = await client.post("/api/whatsapp/webhook", json={
        "MessageSid": "SM999",
        "NumMedia": 0,
        "MessageType": "text",
        "WaId": "15551231234",
        "SmsStatus": "received",
        "To": "whatsapp:+15550001111",
        "From": "whatsapp:+15551231234",
        "Body": "netflix",
    })

    assert resp.status_code == 200
    sent = fake_twilio.messages.calls[0]
    assert "654321" in sent["body"]
    assert sent["to"] == "whatsapp:+15551231234"
    assert sent["from_"] == "whatsapp:+15550001111"


@pytest.mark.asyncio
async def test_whatsapp_webhook_db_mailbox_credential_payload_passed(webhook_client, monkeypatch):
    """When a DB-backed mailbox is found, its credential_payload must be forwarded to get_latest_otp."""
    client, fake_twilio, otp_calls, otp_box = webhook_client
    otp_box["return_value"] = "777777"

    fake_creds = {
        "token": "t1",
        "refresh_token": "rt1",
        "client_id": "cid",
        "client_secret": "cs",
    }
    fake_svc = SimpleNamespace(
        id=1,
        slug="netflix",
        display_name="Netflix",
        keyword_patterns=["netflix"],
        deleted_at=None,
    )
    fake_mb = SimpleNamespace(
        id=1,
        provider=MailboxProvider.GMAIL.value,
        credential_payload=fake_creds,
    )
    fake_cust = SimpleNamespace(id=1, name="Alice", whatsapp_e164="+15551231234")

    monkeypatch.setattr(_whatsapp_router, "list_active_streaming_services", AsyncMock(return_value=[fake_svc]))
    monkeypatch.setattr(
        _whatsapp_router,
        "find_mailbox_for_customer_service",
        AsyncMock(return_value=(fake_mb, fake_cust)),
    )

    resp = await client.post("/api/whatsapp/webhook", data=_FORM)

    assert resp.status_code == 200
    sent = fake_twilio.messages.calls[0]
    assert "777777" in sent["body"]
    assert len(otp_calls) == 1
    assert otp_calls[0]["credential_payload"] == fake_creds
    assert "Netflix" in otp_calls[0]["query"]


@pytest.mark.asyncio
async def test_me_requires_session():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/me")

    assert resp.status_code == 401
