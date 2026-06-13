"""Media probing and audio extraction through FFmpeg tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from music_decomp.config import resolve_ffmpeg_path, resolve_ffprobe_path
from music_decomp.utils.subprocesses import run_command

DetectedMediaKind = Literal["audio", "video"]
ProbeData = dict[str, Any]


class MediaService:
    """Probe media files and extract canonical WAV audio."""

    def __init__(
        self,
        *,
        ffmpeg_path: str | Path | None = None,
        ffprobe_path: str | Path | None = None,
    ) -> None:
        self.ffmpeg_path = Path(ffmpeg_path) if ffmpeg_path is not None else resolve_ffmpeg_path()
        self.ffprobe_path = (
            Path(ffprobe_path) if ffprobe_path is not None else resolve_ffprobe_path()
        )

    def probe(self, path: str | Path) -> ProbeData:
        """Return parsed FFprobe JSON for a media file."""
        input_path = Path(path)
        result = run_command(
            [
                self.ffprobe_path,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                input_path,
            ]
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(f"FFprobe returned invalid JSON for {input_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"FFprobe returned non-object JSON for {input_path}")
        return data

    def extract_audio(self, input_path: str | Path, output_wav: str | Path) -> Path:
        """Extract stereo 44.1 kHz 16-bit WAV audio from a media file."""
        source_path = Path(input_path)
        target_path = Path(output_wav)
        if target_path.parent != Path("."):
            target_path.parent.mkdir(parents=True, exist_ok=True)

        run_command(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                source_path,
                "-vn",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-sample_fmt",
                "s16",
                target_path,
            ]
        )
        return target_path

    def detect_kind(self, path: str | Path) -> DetectedMediaKind:
        """Classify a media file as audio or video from FFprobe stream metadata."""
        data = self.probe(path)
        streams = data.get("streams", [])
        if not isinstance(streams, list):
            raise ValueError(f"FFprobe returned invalid streams metadata for {path}")

        has_audio = any(_stream_type(stream) == "audio" for stream in streams)
        has_video = any(_stream_type(stream) == "video" for stream in streams)

        if has_video:
            return "video"
        if has_audio:
            return "audio"
        raise ValueError(f"Unable to detect media kind for {path}: no audio or video streams")


def _stream_type(stream: object) -> object:
    if isinstance(stream, dict):
        return stream.get("codec_type")
    return None
