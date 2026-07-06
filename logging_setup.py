import sys
from pathlib import Path

from loguru import logger

from config import LOG_DIR


def setup_logging(name: str = "pipeline") -> Path:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / f"{name}.log"

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
    logger.add(
        log_path,
        rotation="20 MB",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
    )
    logger.info(f"Log file: {log_path.resolve()}")
    return log_path
