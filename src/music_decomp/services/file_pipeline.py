"""End-to-end local file probing, extraction, separation, and metadata wiring."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from music_decomp import __version__
from music_decomp.domain.jobs import Device, JobResult, OutputFormat
from music_decomp.domain.media import MediaInput
from music_decomp.services.export_service import (
    JOB_METADATA_FILENAME,
    ExportService,
    safe_filename,
)
from music_decomp.services.media_service import MediaService, ProbeData
from music_decomp.services.separation_service import (
    INTERMEDIATE_DIR_NAME,
    SeparationRunResult,
    SeparationService,
)

PipelineProgressCallback = Callable[[str, str, int | None], None]
InputPreparationCallback = Callable[[MediaInput, Path], None]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class MediaProbeResult:
    """Parsed media details used by the GUI and separation pipeline."""

    media_input: MediaInput
    stream_summary: tuple[str, ...]
    raw_probe_data: ProbeData


@dataclass(frozen=True)
class FileSeparationResult:
    """Successful local-file separation result with output artifact paths."""

    probe: MediaProbeResult
    job_result: JobResult
    separation_result: SeparationRunResult
    output_dir: Path
    log_path: Path
    metadata_path: Path
    highest_is_approximate: bool


class MediaProbeError(ValueError):
    """Raised when FFprobe data cannot be converted into a supported input."""


class FileSeparationPipelineError(RuntimeError):
    """Raised when the end-to-end file pipeline fails after writing artifacts."""

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        output_dir: Path | None = None,
        log_path: Path | None = None,
        metadata_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self.log_path = Path(log_path) if log_path is not None else None
        self.metadata_path = Path(metadata_path) if metadata_path is not None else None


class FileSeparationPipeline:
    """Coordinate media probing, FFmpeg extraction, separation, and metadata."""

    def __init__(
        self,
        *,
        media_service: MediaService | None = None,
        separation_service: SeparationService | None = None,
        export_service: ExportService | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or _default_clock
        self.media_service = media_service or MediaService()
        self.separation_service = separation_service or SeparationService()
        self.export_service = export_service or ExportService(clock=self._clock)

    def probe_input(self, path: str | Path) -> MediaProbeResult:
        """Probe a local audio/video file and return normalized GUI details."""
        input_path = Path(path)
        try:
            probe_data = self.media_service.probe(input_path)
        except Exception as exc:
            raise MediaProbeError(
                f"Unable to probe media file {input_path}: {_exception_text(exc)}"
            ) from exc

        streams = _probe_streams(probe_data, input_path)
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not audio_streams:
            raise MediaProbeError(f"Media file has no audio stream: {input_path}")

        has_video = any(stream.get("codec_type") == "video" for stream in streams)
        first_audio = audio_streams[0]
        media_input = MediaInput(
            kind="video" if has_video else "audio",
            path=input_path,
            title=_probe_title(probe_data, input_path),
            duration_seconds=_probe_duration(probe_data, first_audio),
            sample_rate=_probe_sample_rate(first_audio),
        )
        return MediaProbeResult(
            media_input=media_input,
            stream_summary=tuple(_stream_summary(stream) for stream in streams),
            raw_probe_data=probe_data,
        )

    def run_file(
        self,
        path: str | Path,
        *,
        output_root: str | Path | None = None,
        device: Device = "auto",
        output_format: OutputFormat = "wav",
        progress_callback: PipelineProgressCallback | None = None,
    ) -> FileSeparationResult:
        """Run a local audio/video file through the full Step 8 pipeline."""
        input_path = Path(path)
        started_at = self._clock()
        output_root_path = (
            Path(output_root) if output_root is not None else self.export_service.output_root
        )

        _emit(progress_callback, "probing", "Probing media file.", 5)
        try:
            probe = self.probe_input(input_path)
        except Exception as exc:
            error_message = _exception_text(exc)
            error = self.record_probe_failure(
                input_path,
                output_root=output_root_path,
                device=device,
                output_format=output_format,
                error_message=error_message,
                started_at=started_at,
                ended_at=self._clock(),
            )
            _emit(progress_callback, "failed", "Media probe failed.", None)
            raise error from exc

        return self._run_media_input(
            probe,
            started_at=started_at,
            output_root=output_root_path,
            device=device,
            output_format=output_format,
            progress_callback=progress_callback,
            input_summary_label="probe complete",
            input_stage="extracting",
            input_message="Extracting canonical WAV.",
            input_log_label="extract_audio",
            prepare_input=lambda media_input, canonical_wav: self.media_service.extract_audio(
                media_input.path,
                canonical_wav,
            ),
            done_message="File separation complete.",
            failure_message="File separation failed.",
        )

    def run_recording(
        self,
        media_input: MediaInput,
        *,
        output_root: str | Path | None = None,
        device: Device = "auto",
        output_format: OutputFormat = "wav",
        progress_callback: PipelineProgressCallback | None = None,
    ) -> FileSeparationResult:
        """Run a finalized recording WAV through the Step 9 separation pipeline."""
        if media_input.kind != "recording":
            raise ValueError(
                "run_recording requires MediaInput(kind='recording'); "
                f"got {media_input.kind!r}"
            )
        started_at = self._clock()
        output_root_path = (
            Path(output_root) if output_root is not None else self.export_service.output_root
        )
        _emit(progress_callback, "probing", "Probing recording WAV.", 5)
        try:
            probe = self._probe_recording(media_input)
        except Exception as exc:
            error_message = _exception_text(exc)
            error = self.record_probe_failure(
                media_input.path,
                output_root=output_root_path,
                device=device,
                output_format=output_format,
                error_message=error_message,
                started_at=started_at,
                ended_at=self._clock(),
            )
            _emit(progress_callback, "failed", "Recording probe failed.", None)
            raise error from exc

        return self._run_media_input(
            probe,
            started_at=started_at,
            output_root=output_root_path,
            device=device,
            output_format=output_format,
            progress_callback=progress_callback,
            input_summary_label="recording ready",
            input_stage="extracting",
            input_message="Extracting canonical WAV from recording.",
            input_log_label="recording_extract_audio",
            prepare_input=lambda recording_input, canonical_wav: self.media_service.extract_audio(
                recording_input.path,
                canonical_wav,
            ),
            done_message="Recording separation complete.",
            failure_message="Recording separation failed.",
        )

    def _probe_recording(self, media_input: MediaInput) -> MediaProbeResult:
        """Probe a finalized recording while preserving its recording kind."""
        input_path = media_input.path
        try:
            probe_data = self.media_service.probe(input_path)
        except Exception as exc:
            raise MediaProbeError(
                f"Unable to probe recording WAV {input_path}: {_exception_text(exc)}"
            ) from exc

        streams = _probe_streams(probe_data, input_path)
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not audio_streams:
            raise MediaProbeError(f"Recording WAV has no audio stream: {input_path}")

        first_audio = audio_streams[0]
        probed_duration = _probe_duration(probe_data, first_audio)
        probed_sample_rate = _probe_sample_rate(first_audio)
        normalized_input = MediaInput(
            kind="recording",
            path=input_path,
            title=media_input.title or _probe_title(probe_data, input_path),
            duration_seconds=probed_duration
            if probed_duration is not None
            else media_input.duration_seconds,
            sample_rate=probed_sample_rate or media_input.sample_rate,
        )
        return MediaProbeResult(
            media_input=normalized_input,
            stream_summary=tuple(_stream_summary(stream) for stream in streams),
            raw_probe_data=probe_data,
        )

    def _run_media_input(
        self,
        probe: MediaProbeResult,
        *,
        started_at: datetime,
        output_root: Path,
        device: Device,
        output_format: OutputFormat,
        progress_callback: PipelineProgressCallback | None,
        input_summary_label: str,
        input_stage: str,
        input_message: str,
        input_log_label: str,
        prepare_input: InputPreparationCallback,
        done_message: str,
        failure_message: str,
    ) -> FileSeparationResult:
        """Prepare one supported media input and run separation/metadata writing."""
        job_result: JobResult | None = None
        actual_device = "unknown"
        try:
            _emit(progress_callback, "preparing", "Creating separation job.", 10)
            job_result = self.export_service.prepare_job(
                probe.media_input,
                output_root=output_root,
                device=device,
                output_format=output_format,
            )
            self._log(job_result.log_path, f"job created: {job_result.job.output_dir}")
            self._log(
                job_result.log_path,
                (
                    f"{input_summary_label}: "
                    f"kind={probe.media_input.kind}, "
                    f"duration={probe.media_input.duration_seconds}, "
                    f"sample_rate={probe.media_input.sample_rate}"
                ),
            )
            for summary in probe.stream_summary:
                self._log(job_result.log_path, f"stream: {summary}")

            canonical_wav = (
                job_result.job.output_dir / INTERMEDIATE_DIR_NAME / "input.wav"
            )
            _emit(progress_callback, input_stage, input_message, 25)
            self._log(job_result.log_path, f"{input_log_label} start: {canonical_wav}")
            prepare_input(probe.media_input, canonical_wav)
            self._log(job_result.log_path, f"{input_log_label} complete: {canonical_wav}")

            def separation_progress(stage: str) -> None:
                self._log(job_result.log_path, f"separation stage: {stage}")
                _emit(
                    progress_callback,
                    f"separation.{stage}",
                    _separation_progress_message(stage),
                    _separation_progress_percent(stage),
                )

            self._log(job_result.log_path, "separation start")
            separation_result = self.separation_service.separate(
                job_result,
                canonical_wav,
                progress_callback=separation_progress,
            )
            actual_device = separation_result.actual_device
            self._log(
                job_result.log_path,
                f"separation complete: actual_device={actual_device}",
            )

            _emit(progress_callback, "metadata", "Writing job metadata.", 95)
            metadata_path = self.export_service.write_job_metadata(
                job_result,
                actual_device=actual_device,
                started_at=started_at,
                ended_at=self._clock(),
                status="success",
            )
            self._log(job_result.log_path, f"metadata written: {metadata_path}")
            _emit(progress_callback, "done", done_message, 100)
            return FileSeparationResult(
                probe=probe,
                job_result=job_result,
                separation_result=separation_result,
                output_dir=job_result.job.output_dir,
                log_path=job_result.log_path,
                metadata_path=metadata_path,
                highest_is_approximate=separation_result.highest_is_approximate,
            )
        except Exception as exc:
            error_message = _exception_text(exc)
            if job_result is not None:
                self._log(job_result.log_path, f"pipeline failed: {error_message}")
                try:
                    self.export_service.write_job_metadata(
                        job_result,
                        actual_device=actual_device,
                        started_at=started_at,
                        ended_at=self._clock(),
                        status="failure",
                        error_message=error_message,
                    )
                    self._log(
                        job_result.log_path,
                        f"failure metadata written: {job_result.metadata_path}",
                    )
                except Exception as metadata_exc:
                    self._log(
                        job_result.log_path,
                        "failure metadata write failed: "
                        + _exception_text(metadata_exc),
                )
                _emit(progress_callback, "failed", failure_message, None)
                raise FileSeparationPipelineError(
                    error_message,
                    stage="running",
                    output_dir=job_result.job.output_dir,
                    log_path=job_result.log_path,
                    metadata_path=job_result.metadata_path,
                ) from exc
            _emit(progress_callback, "failed", failure_message, None)
            raise

    def record_probe_failure(
        self,
        path: str | Path,
        *,
        output_root: str | Path | None = None,
        device: Device = "auto",
        output_format: OutputFormat = "wav",
        error_message: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> FileSeparationPipelineError:
        """Create failure artifacts for a probe failure and return a rich error."""
        input_path = Path(path)
        output_root_path = (
            Path(output_root) if output_root is not None else self.export_service.output_root
        )
        output_dir, log_path, metadata_path = self._write_probe_failure_artifacts(
            input_path=input_path,
            output_root=output_root_path,
            started_at=started_at or self._clock(),
            ended_at=ended_at or self._clock(),
            device=device,
            output_format=output_format,
            error_message=error_message,
        )
        return FileSeparationPipelineError(
            error_message,
            stage="probing",
            output_dir=output_dir,
            log_path=log_path,
            metadata_path=metadata_path,
        )

    def _write_probe_failure_artifacts(
        self,
        *,
        input_path: Path,
        output_root: Path,
        started_at: datetime,
        ended_at: datetime,
        device: Device,
        output_format: OutputFormat,
        error_message: str,
    ) -> tuple[Path, Path, Path]:
        title = input_path.stem or input_path.name or "unreadable"
        output_dir = _unique_job_dir(
            output_root
            / f"{self._clock().strftime('%Y%m%d-%H%M%S')}-{safe_filename(title)}-probe-failed"
        )
        log_path = self.export_service.create_job_log(
            output_dir,
            [
                f"job created: {output_dir}",
                f"probe failed: {error_message}",
            ],
        )
        metadata_path = output_dir / JOB_METADATA_FILENAME
        metadata = {
            "app_version": __version__,
            "input_path": str(input_path),
            "input_title": title,
            "requested_device": device,
            "actual_device": "unknown",
            "output_format": output_format,
            "start_timestamp": started_at.isoformat(),
            "end_timestamp": ended_at.isoformat(),
            "status": "failure",
            "failure_stage": "probe",
            "error_message": error_message,
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return output_dir, log_path, metadata_path

    def _log(self, log_path: str | Path, line: str) -> None:
        timestamp = self._clock().isoformat()
        self.export_service.append_job_log(log_path, f"{timestamp} {line}")


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _probe_streams(probe_data: ProbeData, input_path: Path) -> list[dict[str, Any]]:
    streams = probe_data.get("streams")
    if not isinstance(streams, list):
        raise MediaProbeError(f"FFprobe returned invalid streams metadata for {input_path}")
    normalized: list[dict[str, Any]] = []
    for stream in streams:
        if not isinstance(stream, dict):
            raise MediaProbeError(
                f"FFprobe returned invalid stream entry for {input_path}"
            )
        normalized.append(stream)
    return normalized


def _probe_title(probe_data: ProbeData, input_path: Path) -> str:
    format_data = probe_data.get("format")
    if isinstance(format_data, dict):
        tags = format_data.get("tags")
        if isinstance(tags, dict):
            title = tags.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
    return input_path.stem or input_path.name or "untitled"


def _probe_duration(probe_data: ProbeData, audio_stream: dict[str, Any]) -> float | None:
    format_data = probe_data.get("format")
    if isinstance(format_data, dict):
        duration = _parse_positive_float(format_data.get("duration"))
        if duration is not None:
            return duration
    return _parse_positive_float(audio_stream.get("duration"))


def _probe_sample_rate(audio_stream: dict[str, Any]) -> int | None:
    sample_rate = audio_stream.get("sample_rate")
    try:
        parsed = int(str(sample_rate))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_positive_float(value: object) -> float | None:
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _stream_summary(stream: dict[str, Any]) -> str:
    index = stream.get("index", "?")
    codec_type = str(stream.get("codec_type") or "unknown")
    codec_name = str(stream.get("codec_name") or "unknown")
    if codec_type == "audio":
        sample_rate = stream.get("sample_rate")
        channels = stream.get("channels")
        parts = [f"audio #{index}", codec_name]
        if sample_rate is not None:
            parts.append(f"{sample_rate} Hz")
        if channels is not None:
            parts.append(f"{channels} ch")
        return ", ".join(parts)
    if codec_type == "video":
        width = stream.get("width")
        height = stream.get("height")
        dimensions = f"{width}x{height}" if width and height else None
        parts = [f"video #{index}", codec_name]
        if dimensions is not None:
            parts.append(dimensions)
        return ", ".join(parts)
    return f"{codec_type} #{index}, {codec_name}"


def _emit(
    callback: PipelineProgressCallback | None,
    stage: str,
    message: str,
    percent: int | None,
) -> None:
    if callback is not None:
        callback(stage, message, percent)


def _separation_progress_message(stage: str) -> str:
    labels = {
        "preparing": "Preparing separation.",
        "loading_model": "Loading separation model.",
        "separating": "Separating stems.",
        "exporting": "Exporting stems.",
        "done": "Separation stage complete.",
        "failed": "Separation stage failed.",
    }
    return labels.get(stage, f"Separation stage: {stage}.")


def _separation_progress_percent(stage: str) -> int | None:
    return {
        "preparing": 30,
        "loading_model": 40,
        "separating": 60,
        "exporting": 85,
        "done": 92,
    }.get(stage)


def _exception_text(exc: BaseException) -> str:
    return str(exc) or exc.__class__.__name__


def _unique_job_dir(path: Path) -> Path:
    for suffix in ("", "-2", "-3", "-4", "-5"):
        candidate = Path(f"{path}{suffix}") if suffix else path
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"Unable to create unique job directory based on {path}")


__all__ = [
    "FileSeparationPipeline",
    "FileSeparationPipelineError",
    "FileSeparationResult",
    "MediaProbeError",
    "MediaProbeResult",
]
