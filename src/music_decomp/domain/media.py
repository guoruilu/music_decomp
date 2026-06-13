"""Media input domain types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MediaKind = Literal["audio", "video", "recording"]

SUPPORTED_MEDIA_KINDS = ("audio", "video", "recording")


def _validate_supported(value: str, allowed: tuple[str, ...], field_name: str) -> None:
    if value not in allowed:
        expected = ", ".join(allowed)
        raise ValueError(f"Unsupported {field_name} {value!r}; expected one of: {expected}")


@dataclass
class MediaInput:
    """Input media selected or recorded for a separation job."""

    kind: MediaKind
    path: Path
    title: str
    duration_seconds: float | None = None
    sample_rate: int | None = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        _validate_supported(self.kind, SUPPORTED_MEDIA_KINDS, "media kind")
