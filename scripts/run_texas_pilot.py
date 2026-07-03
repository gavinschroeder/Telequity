#!/usr/bin/env python3
"""Convenience entry point for the Texas pilot.

Usage:
    python scripts/run_texas_pilot.py            # real run (needs creds/files)
    python scripts/run_texas_pilot.py --demo     # synthetic, no creds needed
"""
import sys
from pathlib import Path

# Make src/ importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telequity.pipeline import main  # noqa: E402

if __name__ == "__main__":
    main()
