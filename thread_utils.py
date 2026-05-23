import asyncio
import logging
import logging.handlers
import queue
import threading
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class _ThreadFilter(logging.Filter):
    """Accept only records emitted from the registered thread."""

    def __init__(self) -> None:
        self.thread_id: int | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        return record.thread == self.thread_id


class _BlockThreadFilter(logging.Filter):
    """Block records from the thread tracked by a paired _ThreadFilter.

    Added to each primary handler so that worker-thread records never reach
    those handlers directly — they are captured via QueueHandler instead and
    replayed on the calling thread after the worker finishes.
    """

    def __init__(self, tracker: _ThreadFilter) -> None:
        self._tracker = tracker

    def filter(self, record: logging.LogRecord) -> bool:
        if self._tracker.thread_id is None:
            return True  # thread not yet started — allow everything
        return record.thread != self._tracker.thread_id


async def run_in_thread(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run a synchronous function in a thread pool, preserving its log output.

    Logs emitted inside *fn* are captured in a queue and replayed on the calling
    (async) thread after *fn* returns, so they pass through handlers that may be
    context- or thread-sensitive (e.g. Azure Functions stdout capture).

    Usage::

        result = await run_in_thread(my_sync_func, arg1, key=value)
    """
    log_q: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    tracker = _ThreadFilter()
    blocker = _BlockThreadFilter(tracker)

    q_handler = logging.handlers.QueueHandler(log_q)
    q_handler.addFilter(tracker)

    root = logging.getLogger()
    primary = list(root.handlers)

    # Prevent worker-thread records from reaching primary handlers directly
    # so they are not emitted twice (live + replay).
    for h in primary:
        h.addFilter(blocker)
    root.addHandler(q_handler)

    def _wrapper() -> T:
        tracker.thread_id = threading.current_thread().ident
        return fn(*args, **kwargs)

    try:
        result = await asyncio.to_thread(_wrapper)
    finally:
        root.removeHandler(q_handler)
        for h in primary:
            h.removeFilter(blocker)

    # Replay captured records through primary handlers in the main-thread context.
    while True:
        try:
            record = log_q.get_nowait()
        except queue.Empty:
            break
        for h in primary:
            if record.levelno >= h.level:
                try:
                    h.emit(record)
                except Exception:
                    pass

    return result
