"""Настройка журналирования приложения."""

from __future__ import annotations

import logging
from pathlib import Path

from version import __version__


def setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_format = (
        f"%(asctime)s [ChatList v{__version__}] "
        "%(levelname)s %(name)s: %(message)s"
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger("chatlist")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(
        log_dir / "chatlist.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Запуск приложения")
    return logger
