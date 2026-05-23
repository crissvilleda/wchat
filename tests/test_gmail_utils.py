"""Tests for gmail_utils credential loading and OTP extraction.

All external I/O (requests.get, Google token refresh) is mocked so these tests
run without network access or real credentials.
"""

import base64
from unittest.mock import MagicMock

import pytest

import gmail_utils

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = {
    "token": "fake-access-token",
    "refresh_token": "fake-refresh-token",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
}

_ENV_STYLE_PAYLOAD = {
    "GMAIL_TOKEN": "env-access-token",
    "GMAIL_REFRESH_TOKEN": "env-refresh-token",
    "GMAIL_TOKEN_URI": "https://oauth2.googleapis.com/token",
    "GMAIL_CLIENT_ID": "env-client-id",
    "GMAIL_CLIENT_SECRET": "env-client-secret",
}


def _encode_body(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _mock_gmail_responses(monkeypatch, *, otp_text: str, message_id: str = "msg1") -> MagicMock:
    """Patch requests.get to return a message list then a message detail."""
    list_resp = MagicMock()
    list_resp.json.return_value = {
        "messages": [{"id": message_id}],
        "resultSizeEstimate": 1,
    }
    detail_resp = MagicMock()
    detail_resp.json.return_value = {
        "payload": {"body": {"data": _encode_body(otp_text)}}
    }
    mock_get = MagicMock(side_effect=[list_resp, detail_resp])
    monkeypatch.setattr(gmail_utils.requests, "get", mock_get)
    return mock_get


# ---------------------------------------------------------------------------
# _credentials_from_payload — unit tests (no I/O)
# ---------------------------------------------------------------------------

def test_credentials_from_payload_standard_keys():
    creds = gmail_utils._credentials_from_payload(_VALID_PAYLOAD)
    assert creds is not None
    assert creds.token == "fake-access-token"
    assert creds.refresh_token == "fake-refresh-token"
    assert creds.client_id == "fake-client-id"
    assert creds.client_secret == "fake-client-secret"


def test_credentials_from_payload_env_style_keys():
    """Keys matching env var names (GMAIL_TOKEN etc.) are also accepted."""
    creds = gmail_utils._credentials_from_payload(_ENV_STYLE_PAYLOAD)
    assert creds is not None
    assert creds.token == "env-access-token"
    assert creds.refresh_token == "env-refresh-token"
    assert creds.client_id == "env-client-id"


def test_credentials_from_payload_missing_field_returns_none():
    incomplete = {k: v for k, v in _VALID_PAYLOAD.items() if k != "refresh_token"}
    assert gmail_utils._credentials_from_payload(incomplete) is None


def test_credentials_from_payload_empty_returns_none():
    assert gmail_utils._credentials_from_payload({}) is None


# ---------------------------------------------------------------------------
# get_latest_otp with credential_payload — mocked Gmail API
# ---------------------------------------------------------------------------

def test_get_latest_otp_with_payload_returns_otp(monkeypatch):
    """Happy path: valid payload → credentials built → OTP extracted from email."""
    mock_get = _mock_gmail_responses(monkeypatch, otp_text="Tu código es: 123456")

    result = gmail_utils.get_latest_otp(
        'subject:Netflix "inicio de sesión"',
        credential_payload=_VALID_PAYLOAD,
    )

    assert result == "123456"
    # First call lists messages, second fetches the message detail.
    assert mock_get.call_count == 2
    first_call_headers = mock_get.call_args_list[0].kwargs["headers"]
    assert first_call_headers["Authorization"] == "Bearer fake-access-token"


def test_get_latest_otp_with_payload_does_not_read_env_vars(monkeypatch):
    """Providing credential_payload must bypass get_valid_credentials entirely."""
    called = []
    monkeypatch.setattr(gmail_utils, "get_valid_credentials", lambda: called.append(1) or None)
    _mock_gmail_responses(monkeypatch, otp_text="código: 654321")

    gmail_utils.get_latest_otp("subject:test", credential_payload=_VALID_PAYLOAD)

    assert called == [], "get_valid_credentials must not be called when credential_payload is supplied"


def test_get_latest_otp_with_incomplete_payload_returns_none(monkeypatch):
    """Incomplete payload → _credentials_from_payload returns None → abort."""
    incomplete = {"token": "only-token"}
    result = gmail_utils.get_latest_otp("subject:test", credential_payload=incomplete)
    assert result is None


def test_get_latest_otp_no_messages_returns_none(monkeypatch):
    """Gmail returns no matching messages → None."""
    empty_resp = MagicMock()
    empty_resp.json.return_value = {"resultSizeEstimate": 0}
    monkeypatch.setattr(gmail_utils.requests, "get", MagicMock(return_value=empty_resp))

    result = gmail_utils.get_latest_otp("subject:test", credential_payload=_VALID_PAYLOAD)
    assert result is None


def test_get_latest_otp_body_without_otp_returns_none(monkeypatch):
    """Email body exists but contains no 4-6 digit code → None."""
    _mock_gmail_responses(monkeypatch, otp_text="No hay ningún código aquí.")

    result = gmail_utils.get_latest_otp("subject:test", credential_payload=_VALID_PAYLOAD)
    assert result is None


def test_get_latest_otp_multipart_body(monkeypatch):
    """OTP is extracted from the text/plain part of a multipart message."""
    list_resp = MagicMock()
    list_resp.json.return_value = {"messages": [{"id": "msg1"}], "resultSizeEstimate": 1}
    detail_resp = MagicMock()
    detail_resp.json.return_value = {
        "payload": {
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _encode_body("código: 987654")}},
                {"mimeType": "text/html",  "body": {"data": _encode_body("<b>código: 987654</b>")}},
            ]
        }
    }
    monkeypatch.setattr(gmail_utils.requests, "get", MagicMock(side_effect=[list_resp, detail_resp]))

    result = gmail_utils.get_latest_otp("subject:test", credential_payload=_VALID_PAYLOAD)
    assert result == "987654"
