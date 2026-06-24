from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from music_decomp.domain.media import MediaInput
from music_decomp.services.export_service import ExportService
from music_decomp.services.file_pipeline import (
    FileSeparationPipeline,
    FileSeparationPipelineError,
    MediaProbeError,
)
from music_decomp.services.separation_service import (
    SeparationRunResult,
    StemOutputInfo,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixed_time() -> datetime:
    return datetime(2026, 6, 14, 8, 9, 10, tzinfo=timezone.utc)


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeMediaService:
    def __init__(
        self,
        probe_data: dict[str, Any] | None = None,
        *,
        probe_error: Exception | None = None,
        extract_error: Exception | None = None,
    ) -> None:
        self.probe_data = probe_data or _load_fixture("ffprobe_audio.json")
        self.probe_error = probe_error
        self.extract_error = extract_error
        self.probe_calls: list[Path] = []
        self.extract_calls: list[tuple[Path, Path]] = []

    def probe(self, path: str | Path) -> dict[str, Any]:
        input_path = Path(path)
        self.probe_calls.append(input_path)
        if self.probe_error is not None:
            raise self.probe_error
        return self.probe_data

    def extract_audio(self, input_path: str | Path, output_wav: str | Path) -> Path:
        source = Path(input_path)
        target = Path(output_wav)
        self.extract_calls.append((source, target))
        if self.extract_error is not None:
            raise self.extract_error
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"canonical wav")
        return target


class FakeSeparationService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
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
        _emit_fake_progress(progress_callback, "preparing")
        _emit_fake_progress(progress_callback, "loading_model")
        if self.fail:
            raise RuntimeError("separator exploded")
        _emit_fake_progress(progress_callback, "separating")

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
        _emit_fake_progress(progress_callback, "exporting")
        _emit_fake_progress(progress_callback, "done")
        return SeparationRunResult(
            job_result=job_result,
            mixture_wav=mixture_path,
            actual_device="cpu",
            output_files=output_files,
            stem_info=stem_info,
        )


def _emit_fake_progress(callback: object | None, stage: str) -> None:
    if callback is not None:
        callback(stage)  # type: ignore[operator]


def test_probe_input_parses_audio_and_video_metadata(tmp_path: Path) -> None:
    audio_pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(_load_fixture("ffprobe_audio.json")),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path, clock=_fixed_time),
        clock=_fixed_time,
    )
    audio_probe = audio_pipeline.probe_input(tmp_path / "song.wav")

    assert audio_probe.media_input.kind == "audio"
    assert audio_probe.media_input.title == "song"
    assert audio_probe.media_input.duration_seconds == 12.345
    assert audio_probe.media_input.sample_rate == 44100
    assert audio_probe.stream_summary == ("audio #0, pcm_s16le, 44100 Hz, 2 ch",)

    video_pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(_load_fixture("ffprobe_video.json")),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path, clock=_fixed_time),
        clock=_fixed_time,
    )
    video_probe = video_pipeline.probe_input(tmp_path / "clip.mp4")

    assert video_probe.media_input.kind == "video"
    assert video_probe.media_input.duration_seconds == 8.0
    assert video_probe.media_input.sample_rate == 48000
    assert video_probe.stream_summary == (
        "video #0, h264, 1920x1080",
        "audio #1, aac, 48000 Hz, 2 ch",
    )


def test_probe_input_requires_an_audio_stream(tmp_path: Path) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(
            {"streams": [{"index": 0, "codec_type": "video"}], "format": {}}
        ),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path, clock=_fixed_time),
        clock=_fixed_time,
    )

    with pytest.raises(MediaProbeError, match="no audio stream"):
        pipeline.probe_input(tmp_path / "silent.mp4")


def test_run_file_success_writes_log_metadata_and_outputs(tmp_path: Path) -> None:
    media_service = FakeMediaService(_load_fixture("ffprobe_video.json"))
    separation_service = FakeSeparationService()
    pipeline = FileSeparationPipeline(
        media_service=media_service,
        separation_service=separation_service,
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )
    progress: list[tuple[str, str, int | None]] = []

    result = pipeline.run_file(
        tmp_path / "clip.mp4",
        output_root=tmp_path / "outputs",
        device="cpu",
        output_format="wav",
        progress_callback=lambda stage, message, percent: progress.append(
            (stage, message, percent)
        ),
    )

    assert result.output_dir == tmp_path / "outputs" / "20260614-080910-clip"
    assert result.log_path == result.output_dir / "job.log"
    assert result.metadata_path == result.output_dir / "job.json"
    assert result.highest_is_approximate is True
    assert (result.output_dir / "_intermediate" / "input.wav").read_bytes() == b"canonical wav"
    assert set(result.separation_result.output_files) == {
        "vocals",
        "drums",
        "bass",
        "other",
        "lowest",
        "highest",
    }
    assert media_service.extract_calls == [
        (tmp_path / "clip.mp4", result.output_dir / "_intermediate" / "input.wav")
    ]
    assert separation_service.calls == [
        (result.output_dir, result.output_dir / "_intermediate" / "input.wav")
    ]

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "success"
    assert metadata["input_kind"] == "video"
    assert metadata["actual_device"] == "cpu"
    assert metadata["output_format"] == "wav"
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "probe complete: kind=video" in log_text
    assert "extract_audio complete" in log_text
    assert "separation complete: actual_device=cpu" in log_text
    assert "metadata written" in log_text
    assert [entry[0] for entry in progress] == [
        "probing",
        "preparing",
        "extracting",
        "separation.preparing",
        "separation.loading_model",
        "separation.separating",
        "separation.exporting",
        "separation.done",
        "metadata",
        "done",
    ]


def test_run_recording_success_probes_and_extracts_canonical_wav(
    tmp_path: Path,
) -> None:
    recording_path = tmp_path / "browser-take.wav"
    recording_path.write_bytes(b"recorded wav")
    media_service = FakeMediaService(
        {
            "streams": [
                {
                    "index": 0,
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_rate": "48000",
                    "channels": 2,
                }
            ],
            "format": {
                "filename": str(recording_path),
                "format_name": "wav",
                "duration": "31.25",
            },
        }
    )
    separation_service = FakeSeparationService()
    pipeline = FileSeparationPipeline(
        media_service=media_service,
        separation_service=separation_service,
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )
    progress: list[tuple[str, str, int | None]] = []

    result = pipeline.run_recording(
        MediaInput(
            kind="recording",
            path=recording_path,
            title="Browser Take",
            duration_seconds=31.25,
            sample_rate=48_000,
        ),
        output_root=tmp_path / "outputs",
        device="cpu",
        output_format="flac",
        progress_callback=lambda stage, message, percent: progress.append(
            (stage, message, percent)
        ),
    )

    assert result.output_dir == tmp_path / "outputs" / "20260614-080910-Browser Take"
    canonical_wav = result.output_dir / "_intermediate" / "input.wav"
    assert canonical_wav.read_bytes() == b"canonical wav"
    assert result.probe.media_input.kind == "recording"
    assert result.probe.stream_summary == ("audio #0, pcm_s16le, 48000 Hz, 2 ch",)
    assert media_service.probe_calls == [recording_path]
    assert media_service.extract_calls == [(recording_path, canonical_wav)]
    assert separation_service.calls == [(result.output_dir, canonical_wav)]

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "success"
    assert metadata["input_kind"] == "recording"
    assert metadata["input_title"] == "Browser Take"
    assert metadata["input_duration_seconds"] == 31.25
    assert metadata["input_sample_rate"] == 48_000
    assert metadata["output_format"] == "flac"
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "recording ready: kind=recording" in log_text
    assert "recording_extract_audio complete" in log_text
    assert [entry[0] for entry in progress] == [
        "probing",
        "preparing",
        "extracting",
        "separation.preparing",
        "separation.loading_model",
        "separation.separating",
        "separation.exporting",
        "separation.done",
        "metadata",
        "done",
    ]


def test_run_recording_requires_recording_media_kind(tmp_path: Path) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(_load_fixture("ffprobe_audio.json")),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path, clock=_fixed_time),
        clock=_fixed_time,
    )

    with pytest.raises(ValueError, match="kind='recording'"):
        pipeline.run_recording(
            MediaInput(kind="audio", path=tmp_path / "song.wav", title="song")
        )


def test_run_recording_missing_wav_writes_failure_metadata_and_log(
    tmp_path: Path,
) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(
            _load_fixture("ffprobe_audio.json"),
            extract_error=FileNotFoundError(
                f"Recording WAV does not exist: {tmp_path / 'missing.wav'}"
            ),
        ),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )

    with pytest.raises(FileSeparationPipelineError) as exc_info:
        pipeline.run_recording(
            MediaInput(
                kind="recording",
                path=tmp_path / "missing.wav",
                title="Missing Take",
                duration_seconds=4.0,
                sample_rate=48_000,
            ),
            output_root=tmp_path / "outputs",
        )

    error = exc_info.value
    assert error.stage == "running"
    assert error.output_dir == tmp_path / "outputs" / "20260614-080910-Missing Take"
    assert error.log_path is not None
    assert error.metadata_path is not None
    log_text = error.log_path.read_text(encoding="utf-8")
    assert "recording_extract_audio start" in log_text
    assert "Recording WAV does not exist" in log_text
    metadata = json.loads(error.metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failure"
    assert metadata["input_kind"] == "recording"
    assert "Recording WAV does not exist" in metadata["error_message"]


def test_run_file_same_second_collision_gets_unique_job_directories(
    tmp_path: Path,
) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(_load_fixture("ffprobe_audio.json")),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )

    first = pipeline.run_file(tmp_path / "song.wav", output_root=tmp_path / "outputs")
    second = pipeline.run_file(tmp_path / "song.wav", output_root=tmp_path / "outputs")

    assert first.output_dir == tmp_path / "outputs" / "20260614-080910-song"
    assert second.output_dir == tmp_path / "outputs" / "20260614-080910-song-2"
    for result in (first, second):
        assert result.log_path == result.output_dir / "job.log"
        assert result.metadata_path == result.output_dir / "job.json"
        assert result.log_path.is_file()
        assert result.metadata_path.is_file()
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        assert metadata["status"] == "success"


def test_probe_failure_still_creates_failure_job_log_and_metadata(
    tmp_path: Path,
) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(probe_error=OSError("cannot read input")),
        separation_service=FakeSeparationService(),
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )

    with pytest.raises(FileSeparationPipelineError) as exc_info:
        pipeline.run_file(
            tmp_path / "broken.mp3",
            output_root=tmp_path / "outputs",
            device="cpu",
            output_format="flac",
        )

    error = exc_info.value
    assert error.stage == "probing"
    assert error.output_dir == tmp_path / "outputs" / "20260614-080910-broken-probe-failed"
    assert error.log_path is not None
    assert error.metadata_path is not None
    assert "cannot read input" in error.log_path.read_text(encoding="utf-8")
    metadata = json.loads(error.metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failure"
    assert metadata["failure_stage"] == "probe"
    assert metadata["output_format"] == "flac"
    assert "cannot read input" in metadata["error_message"]


def test_separation_failure_writes_failure_metadata_and_log(tmp_path: Path) -> None:
    pipeline = FileSeparationPipeline(
        media_service=FakeMediaService(_load_fixture("ffprobe_audio.json")),
        separation_service=FakeSeparationService(fail=True),
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )

    with pytest.raises(FileSeparationPipelineError) as exc_info:
        pipeline.run_file(tmp_path / "song.wav", output_root=tmp_path / "outputs")

    error = exc_info.value
    assert error.stage == "running"
    assert error.output_dir == tmp_path / "outputs" / "20260614-080910-song"
    assert error.log_path is not None
    assert error.metadata_path is not None
    log_text = error.log_path.read_text(encoding="utf-8")
    assert "extract_audio complete" in log_text
    assert "pipeline failed: separator exploded" in log_text
    assert "failure metadata written" in log_text

    metadata = json.loads(error.metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failure"
    assert metadata["actual_device"] == "unknown"
    assert metadata["error_message"] == "separator exploded"
