"""Output directory, stem path, metadata, and job log management."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from music_decomp import __version__
from music_decomp.domain import DEFAULT_MODEL_NAME, DEFAULT_STEMS
from music_decomp.domain.jobs import Device, JobResult, OutputFormat, SeparationJob
from music_decomp.domain.media import MediaInput
from music_decomp.paths import project_root
from music_decomp.utils.logging import append_text_log, write_text_log

JOB_METADATA_FILENAME = "job.json"
JOB_LOG_FILENAME = "job.log"
WINDOWS_INVALID_FILENAME_CHARS = '<>:"/\\|?*'
JobStatus = Literal["success", "failure"]
Clock = Callable[[], datetime]


def default_output_root() -> Path:
    """Return the default source-mode output root."""
    return project_root() / "outputs"


def safe_filename(value: str, replacement: str = "_") -> str:
    """Return a Windows-safe filename component."""
    if not replacement:
        raise ValueError("replacement must not be empty")

    translation = str.maketrans(
        {character: replacement for character in WINDOWS_INVALID_FILENAME_CHARS}
    )
    safe = value.translate(translation).strip().rstrip(". ")
    return safe or "untitled"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.isoformat()


class ExportService:
    """Prepare output locations and write per-job metadata."""

    def __init__(
        self,
        output_root: str | Path | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.output_root = (
            Path(output_root) if output_root is not None else default_output_root()
        )
        self._clock = clock or _default_clock

    def create_job_directory(
        self,
        media_input: MediaInput,
        output_root: str | Path | None = None,
    ) -> Path:
        """Create and return the timestamped directory for one job."""
        root = Path(output_root) if output_root is not None else self.output_root
        timestamp = self._clock().strftime("%Y%m%d-%H%M%S")
        title = media_input.title or media_input.path.stem
        job_dir = root / f"{timestamp}-{safe_filename(title)}"
        job_dir.mkdir(parents=True, exist_ok=False)
        return job_dir

    def prepare_job(
        self,
        media_input: MediaInput,
        output_root: str | Path | None = None,
        device: Device = "auto",
        model_name: str = DEFAULT_MODEL_NAME,
        output_format: OutputFormat = "wav",
        stems: Sequence[str] = DEFAULT_STEMS,
    ) -> JobResult:
        """Create a job directory, job log, and expected stem output paths."""
        job_dir = self.create_job_directory(media_input, output_root=output_root)
        job = SeparationJob(
            input=media_input,
            output_dir=job_dir,
            device=device,
            model_name=model_name,
            output_format=output_format,
            stems=tuple(stems),
        )
        output_files = self.build_stem_output_paths(job)
        log_path = self.create_job_log(job.output_dir)
        return JobResult(
            job=job,
            output_files=output_files,
            metadata_path=job.output_dir / JOB_METADATA_FILENAME,
            log_path=log_path,
        )

    def build_stem_output_paths(self, job: SeparationJob) -> dict[str, Path]:
        """Build expected output paths for all requested stems."""
        return {
            stem: job.output_dir / f"{safe_filename(stem)}.{job.output_format}"
            for stem in job.stems
        }

    def create_job_log(
        self,
        job_dir: str | Path,
        lines: Iterable[str] = (),
    ) -> Path:
        """Create the plain UTF-8 log file for a job."""
        return write_text_log(Path(job_dir) / JOB_LOG_FILENAME, lines)

    def append_job_log(self, log_path: str | Path, line: str) -> Path:
        """Append one plain UTF-8 line to a job log."""
        return append_text_log(log_path, line)

    def write_job_metadata(
        self,
        result: JobResult,
        actual_device: str,
        started_at: datetime,
        status: JobStatus,
        ended_at: datetime | None = None,
        error_message: str | None = None,
    ) -> Path:
        """Write the final job metadata JSON for a success or failure."""
        if status not in ("success", "failure"):
            raise ValueError("status must be 'success' or 'failure'")

        ended_at = ended_at or self._clock()
        metadata = self._metadata_dict(
            result=result,
            actual_device=actual_device,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            error_message=error_message,
        )
        result.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        result.metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return result.metadata_path

    def _metadata_dict(
        self,
        result: JobResult,
        actual_device: str,
        started_at: datetime,
        ended_at: datetime,
        status: JobStatus,
        error_message: str | None,
    ) -> dict[str, Any]:
        job = result.job
        metadata: dict[str, Any] = {
            "app_version": __version__,
            "input_path": str(job.input.path),
            "input_title": job.input.title,
            "input_kind": job.input.kind,
            "input_duration_seconds": job.input.duration_seconds,
            "input_sample_rate": job.input.sample_rate,
            "model_name": job.model_name,
            "requested_device": job.device,
            "actual_device": actual_device,
            "output_format": job.output_format,
            "stem_filenames": {
                stem: Path(path).name for stem, path in result.output_files.items()
            },
            "start_timestamp": _format_timestamp(started_at),
            "end_timestamp": _format_timestamp(ended_at),
            "status": status,
        }
        if error_message is not None:
            metadata["error_message"] = error_message
        return metadata
