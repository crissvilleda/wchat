from urllib.parse import parse_qs
from typing import Any, Dict

import azure.functions as func


def get_body_from_request(req: func.HttpRequest) -> Dict[str, Any]:
    """Extract the body from an Azure Functions HttpRequest as a flat dict.

    Handles both JSON bodies and ``application/x-www-form-urlencoded`` bodies
    (the format Twilio uses for webhook POSTs).
    """
    body: Dict[str, Any] = {}

    # Try JSON first
    try:
        req_body = req.get_json()
        if isinstance(req_body, dict):
            body.update(req_body)
        elif isinstance(req_body, list):
            body["items"] = req_body
    except ValueError:
        pass

    # Then try form-encoded (Twilio webhooks arrive as application/x-www-form-urlencoded)
    try:
        raw = req.get_body().decode("utf-8")
        parsed = parse_qs(raw)
        for key, value in parsed.items():
            body[key] = value[0] if len(value) == 1 else value
    except ValueError:
        pass

    return body
