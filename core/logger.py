import logging
import os
from pathlib import Path

from config.settings import APP_ROOT, CONFIG


def get_logger(name: str) -> logging.Logger:
    log_dir = Path(CONFIG["paths"]["logs_dir"])
    if not log_dir.is_absolute():
        log_dir = APP_ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    fh = logging.FileHandler(log_dir / "tutor.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger
