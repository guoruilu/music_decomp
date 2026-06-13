from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from music_decomp import __version__
from music_decomp.domain import DEFAULT_STEMS, MediaInput
from music_decomp.services import export_service
from music_decomp.services.export_service import ExportService, safe_filename


def _fixed_time() -> datetime:
    return datetime(2026, 6, 13, 9, 8, 7, tzinfo=timezone.utc)


def _media(tmp_path: Path, title: str = "Song: One/Two") -> MediaInput:
    return MediaInput(
        kind="audio",
        path=tmp_path / "inputs" / "song.wav",
        title=title,
        duration_seconds=12.5,
        sample_rate=44100,
    )


def test_safe_filename_replaces_windows_invalid_characters() -> None:
    assert safe_filename('<bad>: "a/b\\c|d?e*') == "_bad__ _a_b_c_d_e_"


def test_safe_filename_returns_fallback_for_empty_result() -> None:
    assert safe_filename(" . ") == "untitled"


def test_prepare_job_uses_default_outputs_root_in_source_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(export_service, "project_root", lambda: tmp_path)
    service = ExportService(clock=_fixed_time)

    result = service.prepare_job(_media(tmp_path))

    assert result.job.output_dir == tmp_path / "outputs" / "20260613-090807-Song_ One_Two"
    assert result.job.output_dir.is_dir()


def test_prepare_job_accepts_explicit_output_root_and_builds_paths(tmp_path: Path) -> None:
    selected_root = tmp_path / "selected-output"
    service = ExportService(output_root=tmp_path / "default", clock=_fixed_time)

    result = service.prepare_job(
        _media(tmp_path, title='Live<Set>"A"'),
        output_root=selected_root,
        output_format="flac",
        stems=("vocals", "bad/stem"),
    )

    assert result.job.output_dir == selected_root / '20260613-090807-Live_Set__A_'
    assert result.metadata_path == result.job.output_dir / "job.json"
    assert result.log_path == result.job.output_dir / "job.log"
    assert result.log_path.read_bytes() == b""
    assert result.output_files == {
        "vocals": result.job.output_dir / "vocals.flac",
        "bad/stem": result.job.output_dir / "bad_stem.flac",
    }


def test_write_success_metadata_includes_required_fields(tmp_path: Path) -> None:
    service = ExportService(output_root=tmp_path, clock=_fixed_time)
    result = service.prepare_job(_media(tmp_path))
    started_at = datetime(2026, 6, 13, 9, 8, 7, tzinfo=timezone.utc)
    ended_at = datetime(2026, 6, 13, 9, 9, 10, tzinfo=timezone.utc)

    metadata_path = service.write_job_metadata(
        result,
        actual_device="cpu",
        started_at=started_at,
        ended_at=ended_at,
        status="success",
    )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["app_version"] == __version__
    assert metadata["input_path"] == str(tmp_path / "inputs" / "song.wav")
    assert metadata["input_kind"] == "audio"
    assert metadata["input_duration_seconds"] == 12.5
    assert metadata["model_name"] == "htdemucs"
    assert metadata["requested_device"] == "auto"
    assert metadata["actual_device"] == "cpu"
    assert metadata["output_format"] == "wav"
    assert metadata["stem_filenames"] == {
        stem: f"{stem}.wav" for stem in DEFAULT_STEMS
    }
    assert metadata["start_timestamp"] == started_at.isoformat()
    assert metadata["end_timestamp"] == ended_at.isoformat()
    assert metadata["status"] == "success"
    assert "error_message" not in metadata


def test_write_failure_metadata_includes_error_message(tmp_path: Path) -> None:
    service = ExportService(output_root=tmp_path, clock=_fixed_time)
    result = service.prepare_job(_media(tmp_path, title="Broken Song"))
    started_at = datetime(2026, 6, 13, 9, 8, 7, tzinfo=timezone.utc)

    metadata_path = service.write_job_metadata(
        result,
        actual_device="cpu",
        started_at=started_at,
        status="failure",
        error_message="model failed to load",
    )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failure"
    assert metadata["error_message"] == "model failed to load"
    assert metadata["end_timestamp"] == _fixed_time().isoformat()


def test_job_log_helpers_write_plain_utf8_lines(tmp_path: Path) -> None:
    service = ExportService(output_root=tmp_path, clock=_fixed_time)
    result = service.prepare_job(_media(tmp_path))

    service.create_job_log(result.job.output_dir, ["created"])
    service.append_job_log(result.log_path, "completed")

    assert result.log_path.read_bytes() == "created\ncompleted\n".encode("utf-8")
