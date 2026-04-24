from __future__ import annotations

import logging
import os
import sys

from pythonjsonlogger.json import JsonFormatter

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "time",
                "levelname": "level",
                "name": "logger",
            },
        )
    )

    # Replace existing handlers to avoid duplicate logs under reloaders.
    root.handlers = [handler]
    root.propagate = False

    _CONFIGURED = True

