from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, or_


def escape_ilike_pattern(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def ilike_or_columns(
    *columns: Any,
    term: str,
) -> Any:
    esc = escape_ilike_pattern(term)
    pat = f"%{esc}%"
    parts = [c.ilike(pat, escape="\\") for c in columns]
    if not parts:
        raise ValueError("ilike_or_columns needs at least one column")
    if len(parts) == 1:
        return parts[0]
    return or_(*parts)


def keyset_paginate_result[T](
    rows: Sequence[T], *, limit: int, id_getter: str = "id"
) -> tuple[list[T], int | None]:
    """With rows fetched in id order, length up to limit+1; return page and next id for cursor.

    The next id is the id of the last item on this page, used as the key in next_cursor
    (client sends after=… and we use id > decoded_id).
    """
    if len(rows) > limit:
        page = list(rows[:limit])
        last = page[-1]
        next_id: int = getattr(last, id_getter)
        return page, next_id
    return list(rows), None
