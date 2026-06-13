"""Separation job domain types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .media import MediaInput

Device = Literal["auto", "cpu", "cuda"]
OutputFormat = Literal["wav", "flac", "mp3"]

DEFAULT_MODEL_NAME = "htdemucs"
DEFAULT_STEMS = ("vocals", "drums", "bass", "other", "lowest", "highest")
SUPPORTED_DEVICES = ("auto", "cpu", "cuda")
SUPPORTED_OUTPUT_FORMATS = ("wav", "flac", "mp3")


def _validate_supported(value: str, allowed: tuple[str, ...], field_name: str) -> None:
    if value not in allowed:
        expected = ", ".join(allowed)
        raise ValueError(f"Unsupported {field_name} {value!r}; expected one of: {expected}")


@dataclass
class SeparationJob:
    """Configured stem separation job."""

    input: MediaInput
    output_dir: Path
    device: Device = "auto"
    model_name: str = DEFAULT_MODEL_NAME
    output_format: OutputFormat = "wav"
    stems: tuple[str, ...] = DEFAULT_STEMS

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.stems = tuple(self.stems)
        _validate_supported(self.device, SUPPORTED_DEVICES, "device")
        _validate_supported(self.output_format, SUPPORTED_OUTPUT_FORMATS, "output format")


@dataclass
class JobResult:
    """Output paths produced by a completed separation job."""

    job: SeparationJob
    output_files: dict[str, Path]
    metadata_path: Path
    log_path: Path

    def __post_init__(self) -> None:
        self.output_files = {
            stem: Path(output_path) for stem, output_path in self.output_files.items()
        }
        self.metadata_path = Path(self.metadata_path)
        self.log_path = Path(self.log_path)
