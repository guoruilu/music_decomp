"""Plain text log file helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def write_text_log(log_path: str | Path, lines: Iterable[str] = ()) -> Path:
    """Create or replace a UTF-8 text log file."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(str(line) for line in lines)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def append_text_log(log_path: str | Path, line: str) -> Path:
    """Append one UTF-8 text line to a log file."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as log_file:
        log_file.write(f"{line}\n")
    return path
