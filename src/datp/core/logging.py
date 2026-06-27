"""Structured logging setup with Rich console and optional structlog integration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from rich.console import Console
from rich.logging import RichHandler

from datp.core.enums import ArtifactFile

if TYPE_CHECKING:
    from datp.config.models import LoggingConfig

try:
    import structlog
except ImportError:
    structlog = None  # type: ignore[assignment]

console = Console(stderr=True)
_SETUP_DONE = False


def _structlog_shared_processors() -> list[Any]:
    """Return the shared structlog processor chain, or an empty list if structlog is unavailable."""
    if structlog is None:
        return []
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.StackInfoRenderer(),
    ]


@runtime_checkable
class _LoggerProtocol(Protocol):
    def bind(self, **kwargs: Any) -> "_LoggerProtocol": ...
    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...
    def exception(self, event: str, **kwargs: Any) -> None: ...


class _StdlibBoundLogger:
    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None) -> None:
        self._logger = logger
        self._context = {} if context is None else dict(context)

    def bind(self, **kwargs: Any) -> "_StdlibBoundLogger":
        """Return a copy with additional context merged in."""
        return _StdlibBoundLogger(self._logger, {**self._context, **kwargs})

    def _render(self, event: str, **kwargs: Any) -> str:
        """Render a log message with context key=value pairs appended."""
        merged = {**self._context, **kwargs}
        if not merged:
            return event
        fields = " ".join(f"{k}={v!r}" for k, v in sorted(merged.items()))
        return f"{event} {fields}"

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(self._render(event, **kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(self._render(event, **kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(self._render(event, **kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(self._render(event, **kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(self._render(event, **kwargs))


def _parse_level(level: str) -> int:
    """Convert a string level name to its integer constant."""
    parsed = logging.getLevelName(level.upper())
    if isinstance(parsed, int):
        return parsed
    raise ValueError(f"Invalid logging level: {level!r}")


def _make_handlers(
    *, level: str, json: bool, log_dir: Path, max_bytes: int, backup_count: int
) -> list[logging.Handler]:
    """Create and configure console and rotating-file logging handlers."""
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

    if structlog is not None:
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
    else:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        console_handler.setFormatter(fmt)
        file_handler.setFormatter(fmt)

    return [console_handler, file_handler]


def configure_logging(cfg: LoggingConfig, log_dir: Path) -> None:
    """Set up the root logger with console and file handlers; idempotent after first call."""
    global _SETUP_DONE  # noqa: PLW0603
    if _SETUP_DONE:
        return

    if structlog is not None:
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

    for name in ("flwr", "ray", "urllib3", "mlflow", "pytorch_lightning", "lightning"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _SETUP_DONE = True


def get_logger(name: str | None = None) -> _LoggerProtocol:
    """Return a structured logger, falling back to a stdlib wrapper if structlog is unavailable."""
    if structlog is not None:
        return structlog.get_logger(name)
    return _StdlibBoundLogger(
        logging.getLogger("datp" if name is None else name), context=None
    )


def reset_logging() -> None:
    """Remove all handlers and reset structlog defaults."""
    global _SETUP_DONE  # noqa: PLW0603
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    _SETUP_DONE = False
    if structlog is not None:
        structlog.reset_defaults()
