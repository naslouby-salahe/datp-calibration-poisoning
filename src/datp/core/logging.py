from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from rich.console import Console
from rich.logging import RichHandler

from datp.artifacts.names import ArtifactFile

if TYPE_CHECKING:
    from datp.config.models import LoggingConfig

try:  # pragma: no cover - optional dependency in the current environment
    import structlog
except ImportError:  # pragma: no cover - exercised only when structlog is absent
    structlog = None  # type: ignore[assignment]


console = Console(stderr=True)

_SETUP_DONE = False


def _structlog_shared_processors() -> list[Any]:
    """Processors applied before renderer-specific handling.

    ExceptionRenderer is excluded: ConsoleRenderer handles exceptions itself
    (adding it causes a UserWarning), while file paths add it explicitly.
    """
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
    """Protocol satisfied by structlog BoundLogger and _StdlibBoundLogger."""

    def bind(self, **kwargs: Any) -> "_LoggerProtocol": ...
    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...
    def exception(self, event: str, **kwargs: Any) -> None: ...


class _StdlibBoundLogger:
    """Small structlog-like wrapper when structlog is unavailable."""

    def __init__(
        self,
        logger: logging.Logger,
        context: dict[str, Any] | None,
    ) -> None:
        self._logger = logger
        self._context = {} if context is None else dict(context)

    def bind(self, **kwargs: Any) -> "_StdlibBoundLogger":
        return _StdlibBoundLogger(self._logger, {**self._context, **kwargs})

    def _render(self, event: str, **kwargs: Any) -> str:
        merged = {**self._context, **kwargs}
        if not merged:
            return event
        fields = " ".join(f"{key}={merged[key]!r}" for key in sorted(merged))
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
    parsed = logging.getLevelName(level.upper())
    if isinstance(parsed, int):
        return parsed
    raise ValueError(f"Invalid logging level: {level!r}")


def _make_handlers(
    *,
    level: str,
    json: bool,
    log_dir: Path,
    max_bytes: int,
    backup_count: int,
) -> list[logging.Handler]:
    log_dir.mkdir(parents=True, exist_ok=True)

    console_handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    console_handler.setLevel(_parse_level(level))

    file_handler = RotatingFileHandler(
        log_dir / ArtifactFile.LOG,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(_parse_level(level))

    if structlog is not None:
        shared = _structlog_shared_processors()
        console_renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
        file_renderer: Any = (
            structlog.processors.JSONRenderer()
            if json
            else structlog.processors.KeyValueRenderer(
                sort_keys=True,
                key_order=["timestamp", "level", "logger", "event"],
            )
        )
        # Console: ConsoleRenderer renders exceptions itself; no ExceptionRenderer.
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    console_renderer,
                ],
            )
        )
        # File: JSONRenderer/KeyValueRenderer need ExceptionRenderer to capture exc_info.
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
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

    return [console_handler, file_handler]


def configure_logging(cfg: LoggingConfig, log_dir: Path) -> None:
    global _SETUP_DONE  # noqa: PLW0603
    if _SETUP_DONE:
        return

    if structlog is not None:
        shared = _structlog_shared_processors()
        structlog.configure(
            processors=[
                *shared,
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
    """Return a structlog logger when available, else a stdlib wrapper."""
    if structlog is not None:
        return structlog.get_logger(name)
    logger_name = "datp" if name is None else name
    return _StdlibBoundLogger(logging.getLogger(logger_name), context=None)


def reset_logging() -> None:
    """Remove handlers and reset logging globals. Intended for tests only."""
    global _SETUP_DONE  # noqa: PLW0603
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    _SETUP_DONE = False
    if structlog is not None:
        structlog.reset_defaults()
