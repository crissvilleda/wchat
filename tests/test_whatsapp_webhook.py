import pytest
from httpx import ASGITransport, AsyncClient

import orm_models  # noqa: F401 — register models for metadata
import api.db as api_db
from orm_models.base import BaseModel

from api import fastapi_app


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


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepts_twilio_form_and_replies(monkeypatch):
    # In-memory DB so the webhook can open a session for catalog lookup.
    monkeypatch.setenv("DB_URL_ASYNC", "sqlite+aiosqlite:///:memory:")
    api_db.get_async_engine.cache_clear()
    api_db.get_async_sessionmaker.cache_clear()
    engine = api_db.get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    # Ensure deterministic OTP and avoid real Twilio network calls.
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")

    import gmail_utils
    import twilio.http.async_http_client
    import twilio.rest

    monkeypatch.setattr(gmail_utils, "get_latest_otp", lambda query: "123456")
    monkeypatch.setattr(twilio.http.async_http_client, "AsyncTwilioHttpClient", _FakeAsyncTwilioHttpClient)

    fake_twilio_client = _FakeTwilioClient()
    monkeypatch.setattr(twilio.rest, "Client", lambda *a, **k: fake_twilio_client)

    form = {
        "MessageSid": "SM123",
        "NumMedia": "0",
        "MessageType": "text",
        "WaId": "15551231234",
        "SmsStatus": "received",
        "To": "whatsapp:+15550001111",
        "From": "whatsapp:+15551231234",
        "Body": "netflix",
    }

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/whatsapp/webhook", data=form)

    assert resp.status_code == 200
    assert fake_twilio_client.messages.calls, "Expected a Twilio reply to be sent"
    sent = fake_twilio_client.messages.calls[0]
    assert sent["to"] == "whatsapp:+15551231234"
    assert sent["from_"] == "whatsapp:+15550001111"
    assert "123456" in sent["body"]


@pytest.mark.asyncio
async def test_me_requires_session():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/me")

    assert resp.status_code == 401

