import logging
import logging.handlers
import os
import sys
from pathlib import Path

from configs.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    backend_dir = Path(__file__).resolve().parents[2]
    project_root = backend_dir.parent
    log_dir = os.environ.get("APP_LOG_DIR", str(project_root / "logs"))
    log_file = os.path.join(log_dir, "app.log")

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    handlers: list[logging.Handler] = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    file_handler_error: str | None = None
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as exc:
        file_handler_error = str(exc)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)

    if file_handler_error:
        logging.getLogger(__name__).warning(
            "File logging disabled; using console only: %s",
            file_handler_error,
        )

    # reduce noise from external libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
