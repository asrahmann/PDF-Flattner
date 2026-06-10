"""Resolve the user's Desktop directory across OSes (handles OneDrive redirect)."""

import os
from pathlib import Path


def desktop_dir() -> Path:
    """Return the best Desktop directory, falling back to the home directory."""
    home = Path.home()
    candidates: list[Path] = []
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        base = os.environ.get(var)
        if base:
            candidates.append(Path(base) / "Desktop")
    candidates.append(home / "Desktop")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return home
