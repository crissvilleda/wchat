from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.deps.pagination import get_list_context
from api.pagination.cursor import decode_id_cursor, encode_id_cursor
from api.repositories.search import escape_ilike_pattern, keyset_paginate_result


def test_cursor_round_trip():
    t = encode_id_cursor(42)
    assert decode_id_cursor(t) == 42
    # padding stripped in encode
    assert decode_id_cursor(t + "   ") == 42


def test_cursor_rejects_garbage():
    with pytest.raises(ValueError, match="."):
        decode_id_cursor("not-valid-base64!!!")


def test_cursor_rejects_wrong_version():
    import base64
    import json

    bad = base64.urlsafe_b64encode(json.dumps({"v": 999, "id": 1}).encode()).decode().rstrip("=")
    with pytest.raises(ValueError) as e:
        decode_id_cursor(bad)
    assert "version" in str(e.value).lower()


def test_get_list_context_rejects_invalid_after():
    with pytest.raises(HTTPException) as ei:
        get_list_context(limit=25, after="nope", q=None)
    assert ei.value.status_code == 400
    assert ei.value.detail == "Invalid cursor"


def test_get_list_context_strips_and_normalizes():
    c = encode_id_cursor(5)
    ctx = get_list_context(limit=30, after=c, q="  x  ")
    assert ctx.after_id == 5
    assert ctx.q == "x"
    assert ctx.limit == 30


def test_escape_ilike_pattern_wildcards_literal():
    assert escape_ilike_pattern(r"100%_off") == r"100\%\_off"
    assert "\\" in escape_ilike_pattern(r"a\b")


class _IdRow:
    __slots__ = ("id",)

    def __init__(self, i: int) -> None:
        self.id = i


def test_keyset_paginate_result_trims_and_next():
    rows = [_IdRow(1), _IdRow(2), _IdRow(3)]
    page, nxt = keyset_paginate_result(rows, limit=2, id_getter="id")
    assert [r.id for r in page] == [1, 2]
    assert nxt == 2


def test_keyset_paginate_result_no_next_when_short_page():
    rows = [_IdRow(1), _IdRow(2)]
    page, nxt = keyset_paginate_result(rows, limit=2, id_getter="id")
    assert len(page) == 2
    assert nxt is None
