from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Query, status

from api.pagination.cursor import decode_id_cursor
from api.schemas.pagination import MAX_LIST_LIMIT, DEFAULT_LIST_LIMIT


@dataclass(frozen=True, slots=True)
class ListContext:
    limit: int
    after_id: int | None
    q: str | None


def get_list_context(
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    after: str | None = Query(None, description="Cursor from the previous page's next_cursor."),
    q: str | None = Query(
        None,
        min_length=1,
        max_length=200,
        description="Case-insensitive search across resource-specific text fields.",
    ),
) -> ListContext:
    after_id: int | None = None
    if after is not None and (after := after.strip()):
        try:
            after_id = decode_id_cursor(after)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from e
    q_norm = (q or "").strip() or None
    return ListContext(limit=limit, after_id=after_id, q=q_norm)
