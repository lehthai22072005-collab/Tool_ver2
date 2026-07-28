from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_file: str = "reports/stage2.log", verbose: bool = False) -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
        force=True,
    )
    return logging.getLogger("stage2")
