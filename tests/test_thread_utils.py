import logging
import threading

import pytest

from thread_utils import run_in_thread


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CapturingHandler(logging.Handler):
    """Collects every LogRecord it receives."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def _debug_root_level():
    """Lower root logger to DEBUG for the duration of each test."""
    root = logging.getLogger()
    orig = root.level
    root.setLevel(logging.DEBUG)
    yield
    root.setLevel(orig)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_value_is_propagated():
    def _fn(x: int, y: int) -> int:
        return x + y

    result = await run_in_thread(_fn, 3, 7)
    assert result == 10


@pytest.mark.asyncio
async def test_kwargs_forwarded():
    def _fn(*, greeting: str, name: str) -> str:
        return f"{greeting}, {name}!"

    result = await run_in_thread(_fn, greeting="Hello", name="world")
    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_exception_propagates():
    def _fn() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await run_in_thread(_fn)


@pytest.mark.asyncio
async def test_thread_logs_are_replayed():
    """Records emitted inside the thread must appear via the primary handler."""
    cap = _CapturingHandler()
    root = logging.getLogger()
    root.addHandler(cap)
    try:
        def _fn() -> None:
            logging.info("from-thread-info")
            logging.warning("from-thread-warning")

        await run_in_thread(_fn)
    finally:
        root.removeHandler(cap)

    messages = [r.getMessage() for r in cap.records]
    assert "from-thread-info" in messages
    assert "from-thread-warning" in messages


@pytest.mark.asyncio
async def test_main_thread_logs_not_duplicated():
    """Records emitted on the main async context must appear exactly once."""
    cap = _CapturingHandler()
    root = logging.getLogger()
    root.addHandler(cap)
    try:
        logging.info("before-thread")
        await run_in_thread(lambda: None)
        logging.info("after-thread")
    finally:
        root.removeHandler(cap)

    messages = [r.getMessage() for r in cap.records]
    assert messages.count("before-thread") == 1
    assert messages.count("after-thread") == 1


@pytest.mark.asyncio
async def test_runs_in_separate_thread():
    """The callable must execute in a different thread from the event loop."""
    main_thread_id = threading.current_thread().ident
    worker_ids: list[int] = []

    def _fn() -> None:
        worker_ids.append(threading.current_thread().ident)

    await run_in_thread(_fn)
    assert worker_ids and worker_ids[0] != main_thread_id


@pytest.mark.asyncio
async def test_no_thread_log_leaks_to_main():
    """Records from the worker thread must appear exactly once (via replay, not live)."""
    cap = _CapturingHandler()
    root = logging.getLogger()
    root.addHandler(cap)
    try:
        def _fn() -> None:
            logging.info("only-from-thread")

        await run_in_thread(_fn)
    finally:
        root.removeHandler(cap)

    messages = [r.getMessage() for r in cap.records]
    assert messages.count("only-from-thread") == 1
