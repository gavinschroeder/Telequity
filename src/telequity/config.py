"""Configuration loading.

Reads ``config/config.yaml`` plus a ``.env`` file (for secrets) and exposes a
single ``Config`` object. Keeping every analytic choice (weights, thresholds,
paths) in one declarative file is what makes runs reproducible and auditable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

try:  # optional; secrets still load from real env vars if dotenv is absent
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


def project_root() -> Path:
    """Repo root = two levels up from this file (src/telequity/config.py)."""
    return Path(__file__).resolve().parents[2]


@dataclass
class Config:
    """Thin wrapper over the parsed YAML with secret + path helpers."""

    raw: dict[str, Any]
    root: Path

    # ---- dict-style access ------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    # ---- secrets ----------------------------------------------------------
    @staticmethod
    def secret(name: str, default: str | None = None) -> str | None:
        val = os.environ.get(name, default)
        return val or default

    # ---- path resolution --------------------------------------------------
    def path(self, *parts: str) -> Path:
        """Resolve a repo-relative path to an absolute Path."""
        return self.root.joinpath(*parts)

    def data_path(self, kind: str, *parts: str) -> Path:
        """Resolve under a configured data folder (raw/interim/processed/reference)."""
        base = self.raw["paths"][kind]
        return self.root.joinpath(base, *parts)

    # ---- convenience accessors -------------------------------------------
    @property
    def state_fips(self) -> str:
        return self.raw["scope"]["state_fips"]

    @property
    def state_abbr(self) -> str:
        return self.raw["scope"]["state_abbr"]

    @property
    def is_national(self) -> bool:
        """True when the run covers all US counties (no single-state filter)."""
        scope = self.raw["scope"]
        return scope.get("mode") == "national" or not scope.get("state_fips")

    @property
    def scope_slug(self) -> str:
        """Short tag for output filenames: 'us' nationally, else the state abbr."""
        return "us" if self.is_national else str(self.state_abbr).lower()


@lru_cache(maxsize=1)
def load_config(config_path: str | None = None) -> Config:
    """Load and cache the project configuration.

    Args:
        config_path: optional override path to a YAML config.
    """
    root = project_root()
    load_dotenv(root / ".env")
    path = Path(config_path) if config_path else root / "config" / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw=raw, root=root)
