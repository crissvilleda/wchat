"""Gmail credential management and OTP extraction for Azure Functions.

Credentials are loaded from the ``GMAIL_CREDENTIALS_JSON`` environment variable
(a JSON string matching the structure of ``tokens.json``) so they can be stored
as an app setting in Azure.  When that variable is absent the module falls back
to a local ``tokens.json`` file, which is handy during local development.

Usage::

    from gmail_utils import get_latest_otp

    otp = get_latest_otp('subject:Netflix "inicio de sesión"')
"""

import base64
import json
import logging
import os
import re

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_TOKENS_FILE = "tokens.json"
_ENV_CREDENTIALS = "GMAIL_CREDENTIALS_JSON"

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _load_credentials() -> Credentials | None:
    """Load credentials from env var or local tokens file."""
    raw = os.environ.get(_ENV_CREDENTIALS)
    if raw:
        logging.info("gmail_utils: loading credentials from env var %s", _ENV_CREDENTIALS)
        data = json.loads(raw)
    elif os.path.exists(_TOKENS_FILE):
        logging.info("gmail_utils: loading credentials from file %s", _TOKENS_FILE)
        with open(_TOKENS_FILE) as f:
            data = json.load(f)
    else:
        logging.warning(
            "gmail_utils: no credentials found — set %s env var or provide %s",
            _ENV_CREDENTIALS,
            _TOKENS_FILE,
        )
        return None

    return Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data.get("scopes", SCOPES),
    )


def get_valid_credentials() -> Credentials | None:
    """Return valid (possibly refreshed) Gmail credentials, or ``None``."""
    creds = _load_credentials()
    if creds is None:
        return None
    if creds.expired and creds.refresh_token:
        logging.info("gmail_utils: token expired, refreshing...")
        creds.refresh(GoogleRequest())
        logging.info("gmail_utils: token refreshed ok")
    elif creds.expired:
        logging.warning("gmail_utils: token expired and no refresh_token available")
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

def get_latest_otp(query: str) -> str | None:
    """Search Gmail with *query* and return the OTP from the most recent match.

    Returns ``None`` when credentials are unavailable, no messages match, or no
    numeric token can be extracted from the message body.
    """
    logging.info("gmail_utils: get_latest_otp query=%r", query)

    creds = get_valid_credentials()
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

    if "messages" not in res:
        logging.warning("gmail_utils: no messages found for query=%r", query)
        return None

    total = res.get("resultSizeEstimate", "?")
    message_id = res["messages"][0]["id"]
    logging.info("gmail_utils: found ~%s message(s), fetching latest id=%s", total, message_id)

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
