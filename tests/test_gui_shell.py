from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from music_decomp import app, cli
from music_decomp.domain import MediaInput
from music_decomp.services.export_service import ExportService
from music_decomp.services.file_pipeline import FileSeparationPipeline, MediaProbeResult
from music_decomp.services.recorder_service import RecordingDevice
from music_decomp.ui.main_window import (
    HIGHEST_APPROXIMATE_NOTICE,
    MAIN_WINDOW_TABS,
    OUTPUT_FORMAT_OPTIONS,
    format_probe_summary,
    tab_by_key,
    tab_titles,
)
from music_decomp.ui.widgets import MissingPySide6Error
from music_decomp.ui.workers import (
    MediaProbeWorker,
    RecordingWorker,
    SeparationWorker,
    WorkerOutcome,
    WorkerState,
    WorkerUpdate,
)


def _fixed_time() -> datetime:
    return datetime(2026, 6, 14, 8, 9, 10, tzinfo=timezone.utc)


def test_version_still_prints_and_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])

    assert exc_info.value.code == 0
    assert "music-decomp 0.1.0" in capsys.readouterr().out


def test_gui_command_routes_to_app_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str] | None] = []

    def fake_run_gui(argv: list[str] | None = None) -> int:
        calls.append(argv)
        return 23

    monkeypatch.setattr(app, "run_gui", fake_run_gui)

    assert cli.main(["gui"]) == 23
    assert calls == [["music-decomp"]]


def test_gui_command_reports_missing_pyside6(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_gui(argv: list[str] | None = None) -> int:
        raise app.MissingGuiDependencyError("install the gui extra")

    monkeypatch.setattr(app, "run_gui", fake_run_gui)

    assert cli.main(["gui"]) == 1
    assert "install the gui extra" in capsys.readouterr().err


def test_app_run_gui_raises_clear_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "PySide6" or name.startswith("PySide6."):
            raise ImportError("No module named PySide6")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(app.MissingGuiDependencyError) as exc_info:
        app.run_gui(argv=["music-decomp"])

    assert "music-decomp[gui]" in str(exc_info.value)


def test_main_window_tab_spec_is_stable_without_pyside6() -> None:
    assert tab_titles() == ("Files", "Record", "Jobs", "Settings")
    assert len(MAIN_WINDOW_TABS) == 4
    assert HIGHEST_APPROXIMATE_NOTICE == "Outputs include highest (approx.)."

    files = tab_by_key("files")
    assert [control.key for control in files.controls] == [
        "drop_zone",
        "file_picker",
        "selected_file_details",
        "output_format",
        "device",
        "start_separation",
    ]
    assert tuple(option.label for option in OUTPUT_FORMAT_OPTIONS) == (
        "WAV",
        "FLAC",
        "MP3",
    )
    assert tuple(option.value for option in OUTPUT_FORMAT_OPTIONS) == (
        "wav",
        "flac",
        "mp3",
    )


def test_required_tab_controls_are_declared() -> None:
    assert [control.key for control in tab_by_key("record").controls] == [
        "output_device",
        "refresh_devices",
        "record_stop",
        "elapsed_time",
        "level_meter",
        "send_recording",
    ]
    assert [control.key for control in tab_by_key("jobs").controls] == [
        "current_queue",
        "progress_text",
        "status",
        "open_output_folder",
    ]
    assert [control.key for control in tab_by_key("settings").controls] == [
        "output_root",
        "ffmpeg_status",
        "model_status",
        "compute_status",
    ]


def test_workers_are_instantiable_without_qt_and_emit_fallback_signals(tmp_path: Path) -> None:
    updates: list[WorkerUpdate] = []
    outcomes: list[WorkerOutcome] = []
    output_dir = tmp_path / "outputs" / "job"
    result = SimpleNamespace(output_dir=output_dir, highest_is_approximate=True)
    calls: list[tuple[Path, Path | None, str, str]] = []

    class FakePipeline:
        def run_file(
            self,
            input_path: Path,
            *,
            output_root: Path | None,
            output_format: str,
            device: str,
            progress_callback: object,
        ) -> object:
            calls.append((Path(input_path), output_root, output_format, device))
            progress_callback("fake", "Fake pipeline progress.", 42)  # type: ignore[operator]
            return result

    worker = SeparationWorker(
        tmp_path / "song.wav",
        output_root=tmp_path / "outputs",
        output_format="flac",
        device="cpu",
        pipeline=FakePipeline(),
        use_qt_signals=False,
    )
    worker.signals.progress.connect(updates.append)
    worker.signals.finished.connect(outcomes.append)

    worker.queue()
    outcome = worker.run()

    assert worker.state == WorkerState.FINISHED
    assert outcome.state == WorkerState.FINISHED
    assert outcomes == [outcome]
    assert updates[0].stage == "queued"
    assert updates[1].stage == "running"
    assert updates[2] == WorkerUpdate(
        stage="fake",
        message="Fake pipeline progress.",
        percent=42,
    )
    assert outcome.result == result
    assert outcome.message == f"File separation complete: {output_dir}"
    assert calls == [(tmp_path / "song.wav", tmp_path / "outputs", "flac", "cpu")]


def test_separation_worker_routes_recordings_to_recording_pipeline(
    tmp_path: Path,
) -> None:
    updates: list[WorkerUpdate] = []
    recording_input = MediaInput(
        kind="recording",
        path=tmp_path / "recording.wav",
        title="recording",
        duration_seconds=12.0,
        sample_rate=48_000,
    )
    output_dir = tmp_path / "outputs" / "recording-job"
    result = SimpleNamespace(
        output_dir=output_dir,
        probe=SimpleNamespace(media_input=recording_input),
    )
    calls: list[tuple[MediaInput, Path | None, str, str]] = []

    class FakePipeline:
        def run_file(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("recording inputs must not use run_file")

        def run_recording(
            self,
            media_input: MediaInput,
            *,
            output_root: Path | None,
            output_format: str,
            device: str,
            progress_callback: object,
        ) -> object:
            calls.append((media_input, output_root, output_format, device))
            progress_callback(
                "extracting",
                "Extracting canonical WAV from recording.",
                25,
            )  # type: ignore[operator]
            return result

    worker = SeparationWorker(
        media_input=recording_input,
        output_root=tmp_path / "outputs",
        output_format="wav",
        device="auto",
        pipeline=FakePipeline(),
        use_qt_signals=False,
    )
    worker.signals.progress.connect(updates.append)

    outcome = worker.run()

    assert outcome.state == WorkerState.FINISHED
    assert outcome.result == result
    assert outcome.message == f"Recording separation complete: {output_dir}"
    assert calls == [(recording_input, tmp_path / "outputs", "wav", "auto")]
    assert updates[-1] == WorkerUpdate(
        stage="extracting",
        message="Extracting canonical WAV from recording.",
        percent=25,
    )


def test_recording_worker_uses_recorder_service_without_qt(tmp_path: Path) -> None:
    recording_input = MediaInput(
        kind="recording",
        path=tmp_path / "take.wav",
        title="take",
        duration_seconds=3.0,
        sample_rate=48_000,
    )

    class FakeRecorderService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def list_output_devices(self) -> list[RecordingDevice]:
            self.calls.append(("list", None))
            return [
                RecordingDevice(
                    id="speaker-1",
                    name="Speakers",
                    channels=2,
                    is_default=True,
                )
            ]

        def start_recording(self, device_id: str | None = None) -> Path:
            self.calls.append(("start", device_id))
            return tmp_path / "take.wav"

        def stop_recording(self) -> MediaInput:
            self.calls.append(("stop", None))
            return recording_input

    recorder_service = FakeRecorderService()

    list_worker = RecordingWorker(
        action="list_devices",
        recorder_service=recorder_service,
        use_qt_signals=False,
    )
    start_worker = RecordingWorker(
        "speaker-1",
        action="start",
        recorder_service=recorder_service,
        use_qt_signals=False,
    )
    stop_worker = RecordingWorker(
        action="stop",
        recorder_service=recorder_service,
        use_qt_signals=False,
    )

    list_outcome = list_worker.run()
    start_outcome = start_worker.run()
    stop_outcome = stop_worker.run()

    assert list_outcome.result == (
        RecordingDevice(
            id="speaker-1",
            name="Speakers",
            channels=2,
            is_default=True,
        ),
    )
    assert list_outcome.message == "Recording devices ready: 1"
    assert start_outcome.result == tmp_path / "take.wav"
    assert start_outcome.message == f"Recording started: {tmp_path / 'take.wav'}"
    assert stop_outcome.result == recording_input
    assert stop_outcome.message == f"Recording finalized: {tmp_path / 'take.wav'}"
    assert recorder_service.calls == [
        ("list", None),
        ("start", "speaker-1"),
        ("stop", None),
    ]


def test_separation_worker_failure_message_includes_log_path(tmp_path: Path) -> None:
    failed_messages: list[str] = []
    log_path = tmp_path / "outputs" / "job" / "job.log"

    class PipelineError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("pipeline failed")
            self.log_path = log_path

    class FakePipeline:
        def run_file(self, *args: object, **kwargs: object) -> object:
            raise PipelineError()

    worker = SeparationWorker(
        tmp_path / "song.wav",
        pipeline=FakePipeline(),
        use_qt_signals=False,
    )
    worker.signals.failed.connect(failed_messages.append)

    outcome = worker.run()

    assert outcome.state == WorkerState.FAILED
    assert outcome.message == f"pipeline failed\nLog: {log_path}"
    assert failed_messages == [outcome.message]


def test_media_probe_worker_failure_creates_log_artifacts_without_qt(
    tmp_path: Path,
) -> None:
    failed_messages: list[str] = []

    class FailingMediaService:
        def probe(self, path: str | Path) -> object:
            raise OSError("cannot read media")

    pipeline = FileSeparationPipeline(
        media_service=FailingMediaService(),  # type: ignore[arg-type]
        separation_service=object(),  # type: ignore[arg-type]
        export_service=ExportService(output_root=tmp_path / "default", clock=_fixed_time),
        clock=_fixed_time,
    )
    worker = MediaProbeWorker(
        tmp_path / "broken.mp3",
        output_root=tmp_path / "outputs",
        output_format="mp3",
        device="cpu",
        pipeline=pipeline,
        use_qt_signals=False,
    )
    worker.signals.failed.connect(failed_messages.append)

    outcome = worker.run()

    log_path = (
        tmp_path
        / "outputs"
        / "20260614-080910-broken-probe-failed"
        / "job.log"
    )
    metadata_path = log_path.with_name("job.json")
    assert outcome.state == WorkerState.FAILED
    assert failed_messages == [outcome.message]
    assert "cannot read media" in outcome.message
    assert f"Log: {log_path}" in outcome.message
    assert "cannot read media" in log_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failure"
    assert metadata["failure_stage"] == "probe"
    assert metadata["requested_device"] == "cpu"
    assert metadata["output_format"] == "mp3"


def test_worker_classes_expose_expected_shell_state(tmp_path: Path) -> None:
    probe_result = MediaProbeResult(
        media_input=MediaInput(
            kind="video",
            path=tmp_path / "clip.mp4",
            title="clip",
            duration_seconds=8.0,
            sample_rate=48000,
        ),
        stream_summary=("video #0, h264, 1920x1080", "audio #1, aac, 48000 Hz, 2 ch"),
        raw_probe_data={"streams": []},
    )

    class FakePipeline:
        def probe_input(self, path: Path) -> MediaProbeResult:
            assert path == tmp_path / "clip.mp4"
            return probe_result

    media_worker = MediaProbeWorker(
        tmp_path / "clip.mp4",
        pipeline=FakePipeline(),
        use_qt_signals=False,
    )
    recording_worker = RecordingWorker("default", use_qt_signals=False)

    assert media_worker.worker_type == "media_probe"
    assert media_worker.state == WorkerState.IDLE
    media_outcome = media_worker.run()
    assert media_outcome.result == probe_result
    assert media_outcome.message == "Media probe complete: video"

    assert recording_worker.worker_type == "recording"
    assert recording_worker.run().result == {
        "device_id": "default",
        "status": "recording-placeholder",
    }


def test_format_probe_summary_includes_stream_details(tmp_path: Path) -> None:
    probe_result = MediaProbeResult(
        media_input=MediaInput(
            kind="video",
            path=tmp_path / "clip.mp4",
            title="clip",
            duration_seconds=8.0,
            sample_rate=48000,
        ),
        stream_summary=("video #0, h264, 1920x1080", "audio #1, aac, 48000 Hz, 2 ch"),
        raw_probe_data={},
    )

    summary = format_probe_summary(probe_result)

    assert "Kind: video" in summary
    assert "Duration: 8.0 s" in summary
    assert "Sample rate: 48000 Hz" in summary
    assert "- audio #1, aac, 48000 Hz, 2 ch" in summary


def test_qrunnable_adapter_has_clear_missing_pyside6_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_qt_core() -> object:
        raise MissingPySide6Error("PySide6 missing")

    monkeypatch.setattr("music_decomp.ui.workers.import_qt_core", fake_import_qt_core)
    worker = MediaProbeWorker("song.wav", use_qt_signals=False)

    with pytest.raises(MissingPySide6Error, match="PySide6 missing"):
        worker.as_qrunnable()
