from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api import fastapi_app
from api.repositories.errors import ConflictError
from datetime import datetime, timezone


class _FakeStUser:
    def __init__(self, user_id: str):
        self.id = user_id


class _FakeOkSignupResult:
    def __init__(self, user_id: str):
        self.user = _FakeStUser(user_id)


class _FakeAsyncSessionCM:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *_args):
        return None


class _FakeSessionMaker:
    def __call__(self):
        return _FakeAsyncSessionCM()


def _fake_get_session_maker():
    return _FakeSessionMaker()


class _FakeTransactionCM:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *_args):
        return None


class _FakeDbWithBegin:
    def begin(self):
        return _FakeTransactionCM()


class _FakeUser:
    def __init__(
        self,
        *,
        user_id: int,
        entity_id: int,
        name: str,
        email: str,
        supertokens_user_id: str,
        created_at,
        updated_at,
        deleted_at,
    ):
        self.id = user_id
        self.entity_id = entity_id
        self.name = name
        self.email = email
        self.supertokens_user_id = supertokens_user_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at


@pytest.mark.asyncio
async def test_register_endpoint_idempotent_returns_200(monkeypatch):
    import api.auth.router as auth_router

    async def _fake_register_user(**kwargs):
        return (
            _FakeUser(
                user_id=1,
                entity_id=10,
                name="A",
                email="a@example.com",
                supertokens_user_id="st_1",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                deleted_at=None,
            ),
            False,
        )

    monkeypatch.setattr(auth_router, "register_user", _fake_register_user)

    from api.deps.db import get_session_maker

    fastapi_app.dependency_overrides[get_session_maker] = _fake_get_session_maker

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/register",
            json={"email": "a@example.com", "password": "password-password"},
        )

    fastapi_app.dependency_overrides.pop(get_session_maker, None)

    assert resp.status_code == 200
    assert resp.json()["supertokens_user_id"] == "st_1"


@pytest.mark.asyncio
async def test_register_endpoint_conflict_returns_409(monkeypatch):
    import api.auth.router as auth_router

    async def _fake_register_user(**kwargs):
        raise ConflictError("Email already exists")

    monkeypatch.setattr(auth_router, "register_user", _fake_register_user)

    from api.deps.db import get_session_maker

    fastapi_app.dependency_overrides[get_session_maker] = _fake_get_session_maker

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/register",
            json={"email": "a@example.com", "password": "password-password"},
        )

    fastapi_app.dependency_overrides.pop(get_session_maker, None)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_registration_email_exists_links_local_user(monkeypatch):
    import api.auth.registration as reg

    class _EmailExists:
        pass

    # Treat our sentinel as EmailAlreadyExistsError for isinstance checks.
    monkeypatch.setattr(reg, "EmailAlreadyExistsError", _EmailExists)

    async def _fake_sign_up(**kwargs):
        return _EmailExists()

    async def _fake_list_users_by_account_info(*, tenant_id, account_info, do_union_of_account_info=False, user_context=None):
        assert account_info.email == "a@example.com"
        return [_FakeStUser("st_existing")]

    async def _fake_get_local(db, st_user_id):
        assert st_user_id == "st_existing"
        return None

    created: dict[str, object] = {}

    async def _fake_create_local(*, db, supertokens_user_id, email, display_name):
        created["st_user_id"] = supertokens_user_id
        return _FakeUser(
            user_id=2,
            entity_id=20,
            name=display_name,
            email=email,
            supertokens_user_id=supertokens_user_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            deleted_at=None,
        )

    monkeypatch.setattr(reg.emailpassword_asyncio, "sign_up", _fake_sign_up)
    monkeypatch.setattr(reg.supertokens_asyncio, "list_users_by_account_info", _fake_list_users_by_account_info)
    monkeypatch.setattr(reg, "_get_local_user_by_supertokens_user_id", _fake_get_local)
    monkeypatch.setattr(reg, "_create_local_user_for_supertokens_user", _fake_create_local)

    user, created_flag = await reg.register_user(
        db=_FakeDbWithBegin(), email="a@example.com", password="password-password", name=None
    )

    assert created_flag is True
    assert user.supertokens_user_id == "st_existing"
    assert created["st_user_id"] == "st_existing"


@pytest.mark.asyncio
async def test_registration_email_exists_returns_existing_local_user(monkeypatch):
    import api.auth.registration as reg

    class _EmailExists:
        pass

    monkeypatch.setattr(reg, "EmailAlreadyExistsError", _EmailExists)

    async def _fake_sign_up(**kwargs):
        return _EmailExists()

    async def _fake_list_users_by_account_info(*, tenant_id, account_info, do_union_of_account_info=False, user_context=None):
        return [_FakeStUser("st_existing")]

    existing = _FakeUser(
        user_id=3,
        entity_id=30,
        name="Existing",
        email="a@example.com",
        supertokens_user_id="st_existing",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        deleted_at=None,
    )

    async def _fake_get_local(db, st_user_id):
        return existing

    monkeypatch.setattr(reg.emailpassword_asyncio, "sign_up", _fake_sign_up)
    monkeypatch.setattr(reg.supertokens_asyncio, "list_users_by_account_info", _fake_list_users_by_account_info)
    monkeypatch.setattr(reg, "_get_local_user_by_supertokens_user_id", _fake_get_local)

    user, created_flag = await reg.register_user(
        db=object(), email="a@example.com", password="password-password", name=None
    )

    assert created_flag is False
    assert user is existing

