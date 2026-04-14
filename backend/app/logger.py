import logging
import sys
from logging.handlers import RotatingFileHandler
from backend.app.config import settings

LOG_FORMAT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    log_dir = settings.log_path
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(
        filename=log_dir / "agent.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.propagate = False
    return logger
