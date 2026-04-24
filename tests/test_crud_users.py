import pytest
from httpx import ASGITransport, AsyncClient

from api import fastapi_app


@pytest.mark.asyncio
async def test_users_crud_requires_session():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/users")
    assert resp.status_code == 401

