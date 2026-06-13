"""Filesystem path helpers for source and packaged execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "MusicDecomp"


def is_frozen() -> bool:
    """Return True when running from a PyInstaller-frozen executable."""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Return the repository root in source mode or executable directory when frozen."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def app_data_dir() -> Path:
    """Return the user-specific application data directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME

    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a bundled resource path in source or PyInstaller-frozen mode."""
    relative = Path(relative_path)
    if relative.is_absolute():
        msg = f"resource_path expects a relative path, got {relative}"
        raise ValueError(msg)

    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", project_root())).resolve()
    else:
        base = project_root()

    return base / relative
