from __future__ import annotations

import base64
import json

CURSOR_VERSION = 1


def encode_id_cursor(row_id: int) -> str:
    payload = json.dumps({"v": CURSOR_VERSION, "id": row_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def decode_id_cursor(token: str) -> int:
    s = token.strip()
    if not s:
        raise ValueError("empty cursor")
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    try:
        raw = base64.urlsafe_b64decode(s.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as e:
        raise ValueError("invalid cursor encoding") from e
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError("invalid cursor payload") from e
    if not isinstance(data, dict):
        raise ValueError("invalid cursor shape")
    if data.get("v") != CURSOR_VERSION:
        raise ValueError("unsupported cursor version")
    row_id = data.get("id")
    if not isinstance(row_id, int) or row_id < 0:
        raise ValueError("invalid cursor id")
    return row_id
