import logging
import sys
from pathlib import Path


class _CompatLogger:
    def __init__(self) -> None:
        self._logger = logging.getLogger("vbpq")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            handler.setLevel(logging.INFO)
            self._logger.addHandler(handler)

    def remove(self) -> None:
        for handler in list(self._logger.handlers):
            self._logger.removeHandler(handler)
            handler.close()

    def add(self, sink, level="INFO", format=None, encoding=None, **_kwargs) -> None:
        if format and "%(" in format:
            log_format = format
        else:
            log_format = "%(asctime)s | %(levelname)s | %(message)s"
        formatter = logging.Formatter(log_format)
        if hasattr(sink, "write"):
            handler = logging.StreamHandler(sink)
        else:
            Path(sink).parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(sink, encoding=encoding or "utf-8")
        handler.setLevel(getattr(logging, str(level).upper(), logging.INFO))
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def exception(self, message: str) -> None:
        self._logger.exception(message)


logger = _CompatLogger()
