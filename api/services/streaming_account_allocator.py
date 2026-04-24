from __future__ import annotations

from collections.abc import Sequence

from orm_models.streaming_account import StreamingAccount


def pick_streaming_account(
    accounts: Sequence[StreamingAccount],
) -> StreamingAccount | None:
    """
    Minimal pool selection strategy.

    Today we pick the lowest-id active account (stable/deterministic).
    Later strategies (LRU, round-robin, quotas) can be introduced without
    changing the database schema.
    """

    eligible = [
        a
        for a in accounts
        if a.is_active and a.deleted_at is None
    ]
    if not eligible:
        return None

    return min(eligible, key=lambda a: a.id)

