from __future__ import annotations
from datp.types import (
    ByteCount,
    SampleCount,
    SignedCount,
)

import enum
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event, Lock
from typing import TYPE_CHECKING

import structlog
from rich.console import Console
from rich.logging import RichHandler
from structlog.stdlib import get_logger

from datp.core.enums import (
    ArtifactFile,
    LogLevel,
)

if TYPE_CHECKING:
    from datp.config.models import LoggingConfig

__all__ = ["configure_logging", "get_logger", "reset_logging"]


class ExternalLibraryLogger(enum.StrEnum):

    FLOWER = "flwr"
    RAY = "ray"
    URLLIB3 = "urllib3"
    MLFLOW = "mlflow"
    PYTORCH_LIGHTNING = "pytorch_lightning"
    LIGHTNING = "lightning"

console = Console(stderr=True)
_SETUP_DONE = Event()
_SETUP_LOCK = Lock()


def _structlog_shared_processors() -> list[structlog.types.Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.StackInfoRenderer(),
    ]


def _parse_level(level: LogLevel) -> SignedCount:
    match level:
        case LogLevel.DEBUG:
            return logging.DEBUG
        case LogLevel.INFO:
            return logging.INFO
        case LogLevel.WARNING:
            return logging.WARNING
        case LogLevel.ERROR:
            return logging.ERROR
        case LogLevel.CRITICAL:
            return logging.CRITICAL


def _make_handlers(
    *, level: LogLevel, json: bool, log_dir: Path, max_bytes: ByteCount, backup_count: SampleCount
) -> list[logging.Handler]:
    log_dir.mkdir(parents=True, exist_ok=True)
    lvl = _parse_level(level)

    console_handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    console_handler.setLevel(lvl)

    file_handler = RotatingFileHandler(
        log_dir / ArtifactFile.LOG,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(lvl)

    shared = _structlog_shared_processors()
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )
    )
    file_renderer = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.processors.KeyValueRenderer(
            sort_keys=True, key_order=["timestamp", "level", "logger", "event"]
        )
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[*shared, structlog.processors.ExceptionRenderer()],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                file_renderer,
            ],
        )
    )
    return [console_handler, file_handler]


def configure_logging(cfg: LoggingConfig, log_dir: Path) -> None:
    with _SETUP_LOCK:
        if _SETUP_DONE.is_set():
            return

        structlog.configure(
            processors=[
                *_structlog_shared_processors(),
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()

        root.setLevel(_parse_level(cfg.level))
        for handler in _make_handlers(
            level=cfg.level,
            json=cfg.json_format,
            log_dir=log_dir,
            max_bytes=cfg.max_bytes,
            backup_count=cfg.backup_count,
        ):
            root.addHandler(handler)

        for name in ExternalLibraryLogger:
            logging.getLogger(name).setLevel(logging.WARNING)

        _SETUP_DONE.set()


def reset_logging() -> None:
    with _SETUP_LOCK:
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()
        _SETUP_DONE.clear()
        structlog.reset_defaults()
