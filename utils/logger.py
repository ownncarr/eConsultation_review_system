# utils/logger.py
"""
Logger helper. Use get_logger(__name__) from modules to obtain a configured logger
that writes to console and optionally to a rotating file.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import yaml

_default_log_path = "logs/app.log"

def _load_log_path(settings_path: str = "configs/settings.yaml") -> str:
    try:
        with open(settings_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            return cfg.get("logging", {}).get("log_file", _default_log_path)
    except Exception:
        return _default_log_path

def get_logger(name: str, level: int = logging.INFO, settings_path: str = "configs/settings.yaml"):
    """
    Return a logger configured with a StreamHandler and RotatingFileHandler.
    """
    logger = logging.getLogger(name)
    if getattr(logger, "_configured", None):
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Rotating file handler
    log_path = _load_log_path(settings_path)
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # mark configured to avoid duplicate handlers
    logger._configured = True
    return logger
