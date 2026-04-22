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

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

# Env vars — cada campo de tokens.json como variable independiente
_ENV_TOKEN         = "GMAIL_TOKEN"
_ENV_REFRESH_TOKEN = "GMAIL_REFRESH_TOKEN"
_ENV_TOKEN_URI     = "GMAIL_TOKEN_URI"
_ENV_CLIENT_ID     = "GMAIL_CLIENT_ID"
_ENV_CLIENT_SECRET = "GMAIL_CLIENT_SECRET"


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _load_credentials() -> Credentials | None:
    """Load credentials from individual environment variables.

    Variables required:
        GMAIL_TOKEN          – access token
        GMAIL_REFRESH_TOKEN  – refresh token
        GMAIL_TOKEN_URI      – token endpoint (https://oauth2.googleapis.com/token)
        GMAIL_CLIENT_ID      – OAuth client ID
        GMAIL_CLIENT_SECRET  – OAuth client secret
    """
    token         = os.environ.get(_ENV_TOKEN)
    refresh_token = os.environ.get(_ENV_REFRESH_TOKEN)
    token_uri     = os.environ.get(_ENV_TOKEN_URI)
    client_id     = os.environ.get(_ENV_CLIENT_ID)
    client_secret = os.environ.get(_ENV_CLIENT_SECRET)

    missing = [
        name for name, val in {
            _ENV_TOKEN: token,
            _ENV_REFRESH_TOKEN: refresh_token,
            _ENV_TOKEN_URI: token_uri,
            _ENV_CLIENT_ID: client_id,
            _ENV_CLIENT_SECRET: client_secret,
        }.items() if not val
    ]

    if missing:
        logging.warning("gmail_utils: missing env vars: %s", missing)
        return None

    logging.info("gmail_utils: credentials loaded from environment variables")
    return Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
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
