import json
import urllib.parse

import aioresponses
import pytest

from function_app import dummy_redirect_echo, redirect_msgs


class _FakeHttpRequest:
    def __init__(self, method: str, params: dict, body: bytes = b"", headers: dict | None = None):
        self.method = method
        self.params = params
        self._body = body
        self.headers = headers or {}

    def get_body(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_get_returns_ok():
    req = _FakeHttpRequest("GET", {})
    resp = await redirect_msgs(req)
    assert resp.status_code == 200
    assert resp.get_body() == b"ok"


@pytest.mark.asyncio
async def test_post_missing_redirect_to_returns_400():
    req = _FakeHttpRequest("POST", {}, body=b"a=1")
    resp = await redirect_msgs(req)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_post_forwards_body_and_content_type():
    downstream = "http://downstream.test/hook"
    payload = b"MessageSid=SM123&Body=hi"
    with aioresponses.aioresponses() as m:
        m.post(
            downstream,
            status=200,
            body=b"downstream-body",
            content_type="text/xml",
        )
        req = _FakeHttpRequest(
            "POST",
            {"redirect_to": downstream},
            body=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = await redirect_msgs(req)
        assert resp.status_code == 200
        assert resp.get_body() == b"downstream-body"
        m.assert_called_once()


@pytest.mark.asyncio
async def test_post_redirect_to_is_unquoted():
    downstream = "http://downstream.test/path"
    encoded = urllib.parse.quote(downstream, safe="")
    with aioresponses.aioresponses() as m:
        m.post(downstream, status=200, body="ok")
        req = _FakeHttpRequest(
            "POST",
            {"redirect_to": encoded},
            body=b"x=1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = await redirect_msgs(req)
        assert resp.status_code == 200
        m.assert_any_call(downstream, method="POST")


@pytest.mark.asyncio
async def test_post_downstream_non_2xx_returns_502():
    downstream = "http://downstream.test/fail"
    with aioresponses.aioresponses() as m:
        m.post(downstream, status=404, body="not found")
        req = _FakeHttpRequest(
            "POST",
            {"redirect_to": downstream},
            body=b"x=1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp = await redirect_msgs(req)
        assert resp.status_code == 502
        assert b"Bad Gateway" in resp.get_body()


@pytest.mark.asyncio
async def test_dummy_redirect_echo_post_returns_json_echo():
    req = _FakeHttpRequest(
        "POST",
        {},
        body=b"a=1&b=two",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = await dummy_redirect_echo(req)
    assert resp.status_code == 200
    data = json.loads(resp.get_body().decode())
    assert data["ok"] is True
    assert data["body"] == "a=1&b=two"
    assert data["body_length"] == 9
    assert data["content_type"] == "application/x-www-form-urlencoded"
