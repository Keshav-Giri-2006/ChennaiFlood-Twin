"""Logging setup. Lifecycle events are logged as ``event key=value`` lines."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    root = logging.getLogger()
    root.setLevel(level.upper())
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    )
    root.addHandler(handler)
    _CONFIGURED = True


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    parts = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    logger.info("%s %s", event, parts)
