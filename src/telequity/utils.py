"""Shared helpers: logging and tabular I/O."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def write_table(df: pd.DataFrame, path: Path | str, *, index: bool = False) -> Path:
    """Write a DataFrame to CSV or Parquet based on file extension.

    Parent directories are created automatically.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=index)
    else:
        df.to_csv(path, index=index)
    return path


def read_table(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype={"county_fips": "string"})
