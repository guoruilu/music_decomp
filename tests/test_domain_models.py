from __future__ import annotations

from pathlib import Path

import pytest

from music_decomp.domain import (
    DEFAULT_MODEL_NAME,
    DEFAULT_STEMS,
    JobResult,
    MediaInput,
    SeparationJob,
)


def test_media_input_converts_path_like_values() -> None:
    media = MediaInput(kind="audio", path="input/song.wav", title="Song")

    assert media.path == Path("input/song.wav")
    assert media.duration_seconds is None
    assert media.sample_rate is None


def test_separation_job_defaults_and_path_conversion() -> None:
    media = MediaInput(kind="video", path=Path("input/video.mp4"), title="Video")
    job = SeparationJob(input=media, output_dir="outputs/job-001")

    assert job.output_dir == Path("outputs/job-001")
    assert job.device == "auto"
    assert job.model_name == DEFAULT_MODEL_NAME
    assert job.output_format == "wav"
    assert job.stems == DEFAULT_STEMS


def test_separation_job_rejects_unsupported_device() -> None:
    media = MediaInput(kind="audio", path="input/song.wav", title="Song")

    with pytest.raises(ValueError, match="Unsupported device"):
        SeparationJob(input=media, output_dir="outputs/job-001", device="metal")


def test_separation_job_rejects_unsupported_output_format() -> None:
    media = MediaInput(kind="audio", path="input/song.wav", title="Song")

    with pytest.raises(ValueError, match="Unsupported output format"):
        SeparationJob(input=media, output_dir="outputs/job-001", output_format="aac")


def test_job_result_converts_all_output_paths() -> None:
    media = MediaInput(kind="recording", path="recordings/take.wav", title="Take")
    job = SeparationJob(input=media, output_dir="outputs/job-001")
    result = JobResult(
        job=job,
        output_files={"vocals": "outputs/job-001/vocals.wav"},
        metadata_path="outputs/job-001/job.json",
        log_path="outputs/job-001/job.log",
    )

    assert result.output_files == {"vocals": Path("outputs/job-001/vocals.wav")}
    assert result.metadata_path == Path("outputs/job-001/job.json")
    assert result.log_path == Path("outputs/job-001/job.log")
