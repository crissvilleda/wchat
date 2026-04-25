from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

DEFAULT_LIST_LIMIT = 25
MAX_LIST_LIMIT = 100

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
