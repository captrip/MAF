import logging
import os
from logging.handlers import RotatingFileHandler

DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "MAF.log")

_is_configured = False

def init_logging(level: str = DEFAULT_LEVEL, log_file: str = LOG_FILE) -> None:
    global _is_configured
    if _is_configured:
        return

    logger = logging.getLogger()
    logger.setLevel(level)

    formatter = logging.Formatter(
        format="%(asctime)s - %(module)s - %(filename)s : %(lineno)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _is_configured = True

def get_logger(name: str) -> logging.Logger:
    if not _is_configured:
        init_logging()
    return logging.getLogger(name if name else __name__)