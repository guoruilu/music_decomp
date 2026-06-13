from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from music_decomp import app, cli
from music_decomp.ui.main_window import (
    HIGHEST_APPROXIMATE_NOTICE,
    MAIN_WINDOW_TABS,
    OUTPUT_FORMAT_OPTIONS,
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
    worker = SeparationWorker(
        tmp_path / "song.wav",
        output_format="flac",
        device="cpu",
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
    assert outcome.result == {
        "input_path": tmp_path / "song.wav",
        "output_format": "flac",
        "device": "cpu",
        "status": "separation-placeholder",
        "highest_is_approximate": True,
    }


def test_worker_classes_expose_expected_shell_state(tmp_path: Path) -> None:
    media_worker = MediaProbeWorker(tmp_path / "clip.mp4", use_qt_signals=False)
    recording_worker = RecordingWorker("default", use_qt_signals=False)

    assert media_worker.worker_type == "media_probe"
    assert media_worker.state == WorkerState.IDLE
    assert media_worker.run().result == {
        "path": tmp_path / "clip.mp4",
        "status": "probe-placeholder",
    }

    assert recording_worker.worker_type == "recording"
    assert recording_worker.run().result == {
        "device_id": "default",
        "status": "recording-placeholder",
    }


def test_qrunnable_adapter_has_clear_missing_pyside6_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_qt_core() -> object:
        raise MissingPySide6Error("PySide6 missing")

    monkeypatch.setattr("music_decomp.ui.workers.import_qt_core", fake_import_qt_core)
    worker = MediaProbeWorker("song.wav", use_qt_signals=False)

    with pytest.raises(MissingPySide6Error, match="PySide6 missing"):
        worker.as_qrunnable()
