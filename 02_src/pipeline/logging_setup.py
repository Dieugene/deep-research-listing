"""
Logging configuration for the pipeline.
"""
import logging
import sys
from pathlib import Path

from pipeline.config import LOGS_DIR, LEVEL1_LOG_FILE, LEVEL2_LOG_FILE


def get_logger(name: str, log_file: Path = None) -> logging.Logger:
    """
    Return a named logger configured to write to both console and
    the date-stamped log file.

    log_file: override the log file path (defaults to LEVEL1_LOG_FILE).
              Pass LEVEL2_LOG_FILE for level_2 modules.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if log_file is None:
        log_file = LEVEL1_LOG_FILE

    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — use utf-8 with replacement to survive non-latin chars
    # on Windows consoles that use cp1251 or similar encodings.
    import io
    stdout_utf8 = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    ch = logging.StreamHandler(stdout_utf8)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
