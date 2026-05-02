# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**wchatv0** is a FastAPI application deployed on Azure Functions that handles WhatsApp webhooks from Twilio. It extracts OTP tokens from Gmail and sends them back via WhatsApp, supporting multiple services (currently Netflix). The entire API is mounted as a single ASGI application on Azure Functions.

## Architecture & Code Organization

### Directory Structure

```
├── api/                              # FastAPI application (all modules here)
│   ├── __init__.py                  # Exports fastapi_app
│   ├── app.py                       # FastAPI app initialization & router mounting
│   └── routers/
│       └── whatsapp.py              # WhatsApp webhook endpoint & dependencies
├── function_app.py                  # Azure Functions ASGI wrapper
├── schemas.py                       # Pydantic models (MessageSchema)
├── gmail_utils.py                   # Gmail credential & OTP extraction logic
├── request_utils.py                 # Request body parsing utilities
└── tests/
    └── test_whatsapp_webhook.py    # Integration tests with mocked dependencies
```

### Key Design Patterns

**FastAPI Dependency Injection:**
- All modules use FastAPI's `Depends()` for dependency injection
- Custom dependencies in `api/routers/whatsapp.py`:
  - `get_whatsapp_body()` — parses request (JSON or form-encoded)
  - `get_whatsapp_message()` — validates and returns `MessageSchema`
  - Type aliases (`WhatsappBody`, `WhatsappMessage`) reduce boilerplate
- Dependencies are tested through monkeypatching in pytest

**Async/Await:**
- All I/O operations are async (HTTP requests, Twilio API calls, Gmail API)
- `asyncio.to_thread()` wraps sync Gmail operations for non-blocking execution
- Twilio async HTTP client avoids blocking during message sends

**Modular Routing:**
- Each domain (WhatsApp, future integrations) goes in `api/routers/<domain>.py`
- Routers are mounted with `/api` prefix in `api/app.py` to avoid duplication
- Each router has its own prefix (e.g., `/whatsapp`)

## Development Setup & Commands

### Prerequisites

- Python 3.13+
- `uv` package manager (or `pip` with `pyproject.toml`)
- Azure Functions Core Tools (optional, for local Azure testing)
- `dotenvx` — required to decrypt `.env` and inject secrets at runtime (`npm install -g @dotenvx/dotenvx`)

### Installation

```bash
# Install dependencies (using uv)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Common Commands

**Run tests:**
```bash
dotenvx run -- uv run pytest
dotenvx run -- uv run pytest tests/test_whatsapp_webhook.py  # Single test file
dotenvx run -- uv run pytest -v                               # Verbose output
dotenvx run -- uv run pytest -k webhook                       # Filter by test name
```

**Run locally (Azure Functions):**
```bash
dotenvx run -- func start
# API available at http://localhost:7071/api/whatsapp/webhook
```

**Run FastAPI dev server (alternative):**
```bash
dotenvx run -- uv run uvicorn api.app:fastapi_app --reload --port 8000
```

**Format & lint (when available):**
```bash
dotenvx run -- uv run ruff check .
dotenvx run -- uv run ruff format .
```

## Tech Stack & Dependencies

- **FastAPI 0.136+** — ASGI web framework with automatic OpenAPI docs
- **Pydantic 2.12+** — Data validation and serialization
- **Azure Functions 2.0** — Serverless deployment platform
- **Twilio 9.10+** — WhatsApp messaging via Twilio API
- **Google Auth 2.49+** — Gmail OAuth2 credentials
- **pytest 9.0+** — Test framework with async support
- **httpx** — Async HTTP client for testing

## Testing Strategy

**Test Pattern:**
- Use `pytest` with `pytest-asyncio` for async test support
- Mock external dependencies (Twilio, Gmail) with `monkeypatch`
- Test via ASGI transport (`httpx.ASGITransport`) for integration testing
- Environment variables are mocked to avoid real API calls

**Example Test (from `test_whatsapp_webhook.py`):**
```python
async def test_whatsapp_webhook_accepts_twilio_form_and_replies(monkeypatch):
    # Mock env vars
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    
    # Mock external service calls
    monkeypatch.setattr(gmail_utils, "get_latest_otp", lambda q: "123456")
    
    # Test via ASGI transport
    async with AsyncClient(transport=ASGITransport(app=fastapi_app)) as client:
        resp = await client.post("/api/whatsapp/webhook", data=form)
    
    assert resp.status_code == 200
```

## FastAPI Best Practices Applied

1. **Type Hints Everywhere** — Full type annotations for autocomplete & safety
2. **Request/Response Models** — Pydantic `BaseModel` for validation
3. **Dependency Injection** — `Depends()` for reusable, testable code
4. **Async by Default** — `async def` for all endpoints and I/O
5. **Proper HTTP Status Codes** — Explicit `status_code` parameters
6. **Logging** — Built-in Python `logging` module for observability
7. **Configuration via Environment Variables** — Sensitive data never in code

## Environment Variables

> **Always use `dotenvx run --` as a prefix for any command that requires env vars.**
> The project stores secrets in an encrypted `.env` file. dotenvx decrypts it at runtime.
> Never run `pytest`, `uvicorn`, `func start`, or linting commands without this prefix.

**Required for deployment:**
```
TWILIO_ACCOUNT_SID       # Twilio account ID
TWILIO_AUTH_TOKEN        # Twilio auth token
GMAIL_TOKEN              # Gmail OAuth access token
GMAIL_REFRESH_TOKEN      # Gmail refresh token
GMAIL_TOKEN_URI          # Gmail token endpoint
GMAIL_CLIENT_ID          # OAuth client ID
GMAIL_CLIENT_SECRET      # OAuth client secret
```

For local development, use `dotenvx run --` to inject secrets from the encrypted `.env` file. Keep `.env.keys` private and never commit it.

## Key Files & Their Purpose

| File | Purpose |
|------|---------|
| `api/app.py` | FastAPI app setup; mounts all routers with `/api` prefix |
| `api/routers/whatsapp.py` | WhatsApp webhook handler with dependency injection |
| `schemas.py` | Pydantic `MessageSchema` (Twilio webhook payload) |
| `gmail_utils.py` | Gmail credential loading & OTP extraction logic |
| `function_app.py` | Azure Functions ASGI wrapper |
| `request_utils.py` | Utility for parsing request bodies (JSON + form-encoded) |
| `pyproject.toml` | Project metadata, dependencies, pytest config |

## Common Workflows

**Adding a new service (e.g., Discord):**
1. Create `api/routers/discord.py` with its own router and dependencies
2. Import and mount in `api/app.py`: `fastapi_app.include_router(discord_router, prefix="/api")`
3. Add tests to `tests/test_discord.py`

**Modifying WhatsApp webhook response:**
- Edit the `SERVICES` dict or reply logic in `api/routers/whatsapp.py`
- Tests verify reply content is sent to Twilio

**Deploying to Azure Functions:**
- Azure Functions picks up the `function_app` module automatically
- The ASGI app is mounted at runtime via `AsgiFunctionApp` wrapper
- Environment variables are set via Azure portal or `local.settings.json` locally

## Debugging & Logging

- All functions use Python's `logging` module
- Logs are output to Azure Application Insights in production
- For local testing, logs print to console; set `logging.basicConfig()` if needed
- Use `pytest -s` to see logs during test runs
