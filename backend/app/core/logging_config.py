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
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ]

    for handler in handlers:
        handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    logging.basicConfig(level=log_level, handlers=handlers, force=True)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
