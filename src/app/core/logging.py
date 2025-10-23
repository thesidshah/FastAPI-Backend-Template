from __future__ import annotations

import logging
import sys
from typing import Any

import orjson
import structlog
from structlog.typing import Processor

from .config import AppSettings, LogFormat


def _orjson_dumps(value: Any, default: Any = None) -> str:
    # type: ignore
    # pylint: disable=no-member
    return orjson.dumps(value, default=default).decode("utf-8")


def _resolve_level(log_level: str) -> int:
    level = logging.getLevelName(log_level.upper())
    if isinstance(level, str):
        raise ValueError(f"Invalid log level: {log_level}")
    return level


def configure_logging(settings: AppSettings) -> None:
    log_level = _resolve_level(settings.log_level)

    timestamper: Processor = structlog.processors.TimeStamper(
        fmt="iso", utc=True,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer(serializer=_orjson_dumps)
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=renderer,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
