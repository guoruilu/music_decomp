from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from music_decomp import cli
from music_decomp.services.export_service import ExportService
from music_decomp.services.file_pipeline import FileSeparationPipeline
from music_decomp.services.recorder_service import RecordingDevice
from music_decomp.services.separation_service import (
    SeparationRunResult,
    StemOutputInfo,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixed_time() -> datetime:
    return datetime(2026, 6, 24, 7, 8, 9, tzinfo=timezone.utc)


def _completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def test_probe_command_outputs_json_using_mocked_ffprobe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ffmpeg_path = tmp_path / "ffmpeg.exe"
    ffprobe_path = tmp_path / "ffprobe.exe"
    input_path = tmp_path / "song.wav"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    input_path.write_bytes(b"not real audio; ffprobe is mocked")
    monkeypatch.setenv("MUSIC_DECOMP_FFMPEG", str(ffmpeg_path))
    monkeypatch.setenv("MUSIC_DECOMP_FFPROBE", str(ffprobe_path))

    fixture_json = (FIXTURES / "ffprobe_audio.json").read_text(encoding="utf-8")
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed(fixture_json)

    monkeypatch.setattr("music_decomp.services.media_service.run_command", fake_run_command)

    assert cli.main(["probe", str(input_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output == {
        "duration_seconds": 12.345,
        "kind": "audio",
        "path": str(input_path),
        "sample_rate": 44100,
        "streams": ["audio #0, pcm_s16le, 44100 Hz, 2 ch"],
        "title": "song",
    }
    assert calls == [
        [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            input_path,
        ]
    ]


def test_separate_command_uses_pipeline_with_local_file_and_fake_services(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "short.wav"
    input_path.write_bytes(b"short local input")
    media_service = _FakeMediaService()
    separation_service = _FakeSeparationService()
    pipeline = FileSeparationPipeline(
        media_service=media_service,  # type: ignore[arg-type]
        separation_service=separation_service,  # type: ignore[arg-type]
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )
    monkeypatch.setattr(cli, "_create_file_pipeline", lambda: pipeline)

    exit_code = cli.main(
        [
            "separate",
            str(input_path),
            "--out",
            str(tmp_path / "outputs"),
            "--device",
            "cpu",
            "--format",
            "wav",
        ]
    )

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    output_dir = tmp_path / "outputs" / "20260624-070809-short"
    assert exit_code == 0
    assert output["status"] == "success"
    assert output["input_kind"] == "audio"
    assert output["output_dir"] == str(output_dir)
    assert output["metadata_path"] == str(output_dir / "job.json")
    assert output["log_path"] == str(output_dir / "job.log")
    assert output["highest_is_approximate"] is True
    assert set(output["output_files"]) == {
        "bass",
        "drums",
        "highest",
        "lowest",
        "other",
        "vocals",
    }
    assert media_service.extract_calls == [
        (input_path, output_dir / "_intermediate" / "input.wav")
    ]
    assert separation_service.calls == [(output_dir, output_dir / "_intermediate" / "input.wav")]
    assert "probing (5%): Probing media file." in captured.err
    assert "done (100%): File separation complete." in captured.err


def test_list_recording_devices_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeRecorderService:
        def list_output_devices(self) -> list[RecordingDevice]:
            return [
                RecordingDevice(
                    id="speaker-1",
                    name="Speakers",
                    channels=2,
                    is_default=True,
                )
            ]

    monkeypatch.setattr(cli, "_create_recorder_service", FakeRecorderService)

    assert cli.main(["list-recording-devices"]) == 0

    assert json.loads(capsys.readouterr().out) == [
        {
            "channels": 2,
            "id": "speaker-1",
            "is_default": True,
            "name": "Speakers",
        }
    ]


def test_command_errors_hide_tracebacks_unless_debug_is_passed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingPipeline:
        def probe_input(self, path: Path) -> object:
            raise RuntimeError(f"cannot probe {path}")

    monkeypatch.setattr(cli, "_create_file_pipeline", FailingPipeline)

    assert cli.main(["probe", "broken.wav"]) == 1
    default_error = capsys.readouterr().err
    assert "Error: cannot probe broken.wav" in default_error
    assert "Traceback" not in default_error

    assert cli.main(["probe", "broken.wav", "--debug"]) == 1
    debug_error = capsys.readouterr().err
    assert "Traceback" in debug_error
    assert "RuntimeError: cannot probe broken.wav" in debug_error


class _FakeMediaService:
    def __init__(self) -> None:
        self.extract_calls: list[tuple[Path, Path]] = []

    def probe(self, path: str | Path) -> dict[str, Any]:
        input_path = Path(path)
        return {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_rate": "44100",
                    "channels": 2,
                }
            ],
            "format": {
                "filename": str(input_path),
                "format_name": "wav",
                "duration": "1.0",
            },
        }

    def extract_audio(self, input_path: str | Path, output_wav: str | Path) -> Path:
        source = Path(input_path)
        target = Path(output_wav)
        self.extract_calls.append((source, target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"canonical wav")
        return target


class _FakeSeparationService:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def separate(
        self,
        result: object,
        mixture_wav: str | Path,
        progress_callback: object | None = None,
    ) -> SeparationRunResult:
        job_result = result
        mixture_path = Path(mixture_wav)
        self.calls.append((job_result.job.output_dir, mixture_path))
        for stage in ("preparing", "loading_model", "separating", "exporting", "done"):
            if progress_callback is not None:
                progress_callback(stage)  # type: ignore[operator]

        output_files: dict[str, Path] = {}
        stem_info: dict[str, StemOutputInfo] = {}
        for stem, output_path in job_result.output_files.items():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(f"{stem} output".encode("utf-8"))
            output_files[stem] = output_path
            stem_info[stem] = StemOutputInfo(
                stem=stem,
                path=output_path,
                source="mixture_highpass_band" if stem == "highest" else "demucs",
                approximate=stem == "highest",
            )

        return SeparationRunResult(
            job_result=job_result,
            mixture_wav=mixture_path,
            actual_device="cpu",
            output_files=output_files,
            stem_info=stem_info,
        )
