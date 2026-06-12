"""Gmail credential management and OTP extraction for Azure Functions.

Credentials must be supplied as a ``credential_payload`` dict when calling
:func:`get_latest_otp`.  The dict must contain the keys ``token``,
``refresh_token``, ``token_uri``, ``client_id``, and ``client_secret``.

Usage::

    from gmail_utils import get_latest_otp

    otp = get_latest_otp('subject:Netflix "inicio de sesión"', credential_payload=mailbox.credential_payload)
"""

import base64
import logging
import re

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

_REQUIRED_CREDENTIAL_KEYS = (
    "access_token", "refresh_token", "token_uri", "client_id", "client_secret")


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _credentials_from_payload(payload: dict) -> Credentials | None:
    """Build credentials from a JSON object (e.g. mailbox.credential_payload)."""
    if not payload:
        return None
    missing = [k for k in _REQUIRED_CREDENTIAL_KEYS if not payload.get(k)]
    if missing:
        logging.warning(
            "gmail_utils: credential payload missing keys: %s", missing)
        return None
    token = payload["access_token"]
    refresh_token = payload["refresh_token"]
    token_uri = payload["token_uri"]
    client_id = payload["client_id"]
    client_secret = payload["client_secret"]
    token = payload["access_token"]
    refresh_token = payload["refresh_token"]
    token_uri = payload["token_uri"]
    client_id = payload["client_id"]
    client_secret = payload["client_secret"]
    return Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def _ensure_valid(creds: Credentials) -> Credentials | None:
    # Always refresh when a refresh_token is available. Stored access tokens
    # are built without an expiry datetime, so creds.expired is always False
    # even when the token is stale — forcing a refresh avoids 401s.
    if creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            logging.info("gmail_utils: token refreshed ok")
        except Exception as exc:
            logging.error("gmail_utils: token refresh failed: %s", exc)
            return None
    elif not creds.valid:
        logging.warning(
            "gmail_utils: token invalid and no refresh_token available")
        return None
    logging.info("gmail_utils: credentials valid")
    return creds if creds.valid else None


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

def _extract_body(payload: dict) -> str:
    """Return the plain-text body of a Gmail message payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
    else:
        data = payload["body"].get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8")
    return ""


def _extract_otp(text: str) -> str | None:
    """Extract the first 4–6 digit code found in *text*."""
    match = re.search(r"\b\d{4,6}\b", text)
    return match.group() if match else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_profile_email(access_token: str) -> str | None:
    """Return the email address of the authorized Gmail account."""
    try:
        res = requests.get(
            f"{_GMAIL_API}/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        res.raise_for_status()
        return res.json().get("emailAddress")
    except Exception as exc:
        logging.error("gmail_utils: get_profile_email failed: %s", exc)
        return None


def get_latest_otp(query: str, *, credential_payload: dict | None = None) -> str | None:
    """Search Gmail with *query* and return the OTP from the most recent match.

    *credential_payload* is required and must contain the five OAuth fields.

    Returns ``None`` when credentials are unavailable, no messages match, or no
    numeric token can be extracted from the message body.
    """
    logging.info("gmail_utils: get_latest_otp query=%r", query)

    if credential_payload is None:
        logging.error("gmail_utils: aborting — credential_payload is required")
        return None
    raw = _credentials_from_payload(credential_payload)
    creds = _ensure_valid(raw) if raw is not None else None
    if creds is None:
        logging.error("gmail_utils: aborting — no valid credentials")
        return None

    headers = {"Authorization": f"Bearer {creds.token}"}

    logging.info("gmail_utils: searching messages...")
    res = requests.get(
        f"{_GMAIL_API}/messages",
        params={"q": query},
        headers=headers,
        timeout=10,
    ).json()

    logging.info("gmail_utils: res=%r", res)

    if "messages" not in res:
        logging.warning("gmail_utils: no messages found for query=%r", query)
        return None

    total = res.get("resultSizeEstimate", "?")
    message_id = res["messages"][0]["id"]
    logging.info(
        "gmail_utils: found ~%s message(s), fetching latest id=%s", total, message_id)

    msg = requests.get(
        f"{_GMAIL_API}/messages/{message_id}",
        headers=headers,
        timeout=10,
    ).json()

    body = _extract_body(msg["payload"])
    logging.info("gmail_utils: body preview=%r", body[:120])

    otp = _extract_otp(body)
    logging.info("gmail_utils: extracted otp=%r", otp)
    return otp
