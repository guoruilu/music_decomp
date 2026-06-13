"""Runtime configuration helpers."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import is_frozen, resource_path

FFMPEG_ENV_VAR = "MUSIC_DECOMP_FFMPEG"
FFPROBE_ENV_VAR = "MUSIC_DECOMP_FFPROBE"
FFMPEG_BUNDLED_PATH = Path("vendor/ffmpeg/bin/ffmpeg.exe")
FFPROBE_BUNDLED_PATH = Path("vendor/ffmpeg/bin/ffprobe.exe")


class MissingExecutableError(FileNotFoundError):
    """Raised when a required bundled or configured executable cannot be found."""


@dataclass(frozen=True)
class FFmpegPaths:
    """Resolved FFmpeg executable paths."""

    ffmpeg: Path
    ffprobe: Path


def resolve_ffmpeg_path() -> Path:
    """Resolve the FFmpeg executable path."""
    return _resolve_executable(
        executable_name="ffmpeg",
        env_var=FFMPEG_ENV_VAR,
        bundled_relative_path=FFMPEG_BUNDLED_PATH,
    )


def resolve_ffprobe_path() -> Path:
    """Resolve the FFprobe executable path."""
    return _resolve_executable(
        executable_name="ffprobe",
        env_var=FFPROBE_ENV_VAR,
        bundled_relative_path=FFPROBE_BUNDLED_PATH,
    )


def resolve_ffmpeg_paths() -> FFmpegPaths:
    """Resolve both FFmpeg and FFprobe executable paths."""
    return FFmpegPaths(ffmpeg=resolve_ffmpeg_path(), ffprobe=resolve_ffprobe_path())


def _resolve_executable(
    *,
    executable_name: str,
    env_var: str,
    bundled_relative_path: Path,
) -> Path:
    env_path = _env_path(env_var)
    if env_path is not None:
        if env_path.is_file():
            return env_path
        raise MissingExecutableError(
            f"{executable_name} path from {env_var} does not exist: {env_path}"
        )

    bundled_path = resource_path(bundled_relative_path)
    if bundled_path.is_file():
        return bundled_path

    if _development_mode():
        system_path = shutil.which(executable_name)
        if system_path:
            return Path(system_path)

    search_scope = "environment variables and bundled executable"
    if _development_mode():
        search_scope += " or system PATH"
    raise MissingExecutableError(
        f"Unable to find {executable_name}; checked {env_var}, "
        f"{bundled_path}, and {search_scope}."
    )


def _env_path(env_var: str) -> Path | None:
    value = os.environ.get(env_var)
    if not value:
        return None
    return Path(value).expanduser()


def _development_mode() -> bool:
    return not is_frozen()
