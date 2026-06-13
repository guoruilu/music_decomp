"""Main window shell for the desktop GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from music_decomp.paths import project_root

from .widgets import (
    ControlSpec,
    OptionSpec,
    TabSpec,
    combo_value,
    create_drop_zone,
    create_labeled_row,
    create_status_label,
    format_elapsed,
    import_qt_modules,
    populate_combo_box,
    selected_file_summary,
)
from .workers import SeparationWorker, WorkerOutcome, WorkerUpdate

OUTPUT_FORMAT_OPTIONS = (
    OptionSpec("WAV", "wav"),
    OptionSpec("FLAC", "flac"),
    OptionSpec("MP3", "mp3"),
)
DEVICE_OPTIONS = (
    OptionSpec("Auto", "auto"),
    OptionSpec("CPU", "cpu"),
    OptionSpec("CUDA", "cuda"),
)
HIGHEST_APPROXIMATE_NOTICE = "Outputs include highest (approx.)."

MAIN_WINDOW_TABS = (
    TabSpec(
        key="files",
        title="Files",
        controls=(
            ControlSpec("drop_zone", "Drag/drop zone", "drop_zone"),
            ControlSpec("file_picker", "Choose File", "button"),
            ControlSpec("selected_file_details", "Selected file details", "label"),
            ControlSpec(
                "output_format",
                "Output format",
                "combo",
                OUTPUT_FORMAT_OPTIONS,
            ),
            ControlSpec("device", "Device", "combo", DEVICE_OPTIONS),
            ControlSpec("start_separation", "Start Separation", "button"),
        ),
    ),
    TabSpec(
        key="record",
        title="Record",
        controls=(
            ControlSpec("output_device", "Output device", "combo"),
            ControlSpec("refresh_devices", "Refresh Devices", "button"),
            ControlSpec("record_stop", "Record/Stop", "button"),
            ControlSpec("elapsed_time", "Elapsed time", "label"),
            ControlSpec("level_meter", "Level meter", "meter"),
            ControlSpec(
                "send_recording",
                "Send Recording To Separation",
                "button",
            ),
        ),
    ),
    TabSpec(
        key="jobs",
        title="Jobs",
        controls=(
            ControlSpec("current_queue", "Current queue", "list"),
            ControlSpec("progress_text", "Progress", "label"),
            ControlSpec("status", "Status", "label"),
            ControlSpec("open_output_folder", "Open Output Folder", "button"),
        ),
    ),
    TabSpec(
        key="settings",
        title="Settings",
        controls=(
            ControlSpec("output_root", "Output root", "path_selector"),
            ControlSpec("ffmpeg_status", "FFmpeg status", "label"),
            ControlSpec("model_status", "Model status", "label"),
            ControlSpec("compute_status", "CPU/GPU status", "label"),
        ),
    ),
)


class MainWindow:
    """Factory class that returns a Qt main window only when PySide6 is present."""

    def __new__(cls, *args: object, **kwargs: object) -> object:
        qt = import_qt_modules()
        qt_main_window_class = _create_qt_main_window_class(qt)
        return qt_main_window_class(*args, **kwargs)


def tab_titles() -> tuple[str, ...]:
    """Return the stable main-window tab titles."""
    return tuple(tab.title for tab in MAIN_WINDOW_TABS)


def tab_by_key(key: str) -> TabSpec:
    """Return one stable tab spec by key."""
    for tab in MAIN_WINDOW_TABS:
        if tab.key == key:
            return tab
    raise KeyError(key)


def _create_qt_main_window_class(qt: Any) -> type[Any]:
    QtCore = qt.QtCore
    QtGui = qt.QtGui
    QtWidgets = qt.QtWidgets

    class QtMainWindow(QtWidgets.QMainWindow):  # type: ignore[misc, valid-type]
        def __init__(self, parent: object | None = None) -> None:
            super().__init__(parent)
            self.selected_file: Path | None = None
            self.current_output_folder: Path | None = None
            self.output_root = project_root() / "outputs"
            self._active_workers: list[object] = []
            self._active_runnables: list[object] = []
            self._recording = False
            self._record_elapsed_seconds = 0

            self.setWindowTitle("Music Decomp")
            self.resize(980, 640)

            self.record_timer = QtCore.QTimer(self)
            self.record_timer.timeout.connect(self._tick_recording_timer)

            central = QtWidgets.QWidget()
            root_layout = QtWidgets.QVBoxLayout(central)
            root_layout.setContentsMargins(12, 12, 12, 12)
            root_layout.setSpacing(8)

            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setObjectName("mainTabs")
            root_layout.addWidget(self.tabs, 1)

            self.global_error_label = create_status_label(qt)
            self.global_error_label.setObjectName("globalErrorLabel")
            self.global_error_label.setStyleSheet("color: #9d1f2a;")
            root_layout.addWidget(self.global_error_label)

            self.setCentralWidget(central)
            self.tabs.addTab(self._build_files_tab(), "Files")
            self.tabs.addTab(self._build_record_tab(), "Record")
            self.tabs.addTab(self._build_jobs_tab(), "Jobs")
            self.tabs.addTab(self._build_settings_tab(), "Settings")

        def _build_files_tab(self) -> object:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setSpacing(10)

            self.file_drop_zone = create_drop_zone(qt, self._set_selected_file)
            layout.addWidget(self.file_drop_zone)

            top_row = QtWidgets.QHBoxLayout()
            self.file_picker_button = QtWidgets.QPushButton("Choose File")
            self.file_picker_button.setObjectName("filePickerButton")
            self.file_picker_button.clicked.connect(self._choose_file)
            top_row.addWidget(self.file_picker_button)

            self.selected_file_label = create_status_label(qt, "No file selected")
            self.selected_file_label.setObjectName("selectedFileDetails")
            top_row.addWidget(self.selected_file_label, 1)
            layout.addLayout(top_row)

            controls = QtWidgets.QHBoxLayout()
            self.output_format_combo = QtWidgets.QComboBox()
            self.output_format_combo.setObjectName("outputFormatSelector")
            populate_combo_box(self.output_format_combo, OUTPUT_FORMAT_OPTIONS)
            controls.addWidget(
                create_labeled_row(qt, "Output format", self.output_format_combo),
                1,
            )

            self.device_combo = QtWidgets.QComboBox()
            self.device_combo.setObjectName("deviceSelector")
            populate_combo_box(self.device_combo, DEVICE_OPTIONS)
            controls.addWidget(create_labeled_row(qt, "Device", self.device_combo), 1)
            layout.addLayout(controls)

            self.start_separation_button = QtWidgets.QPushButton("Start Separation")
            self.start_separation_button.setObjectName("startSeparationButton")
            self.start_separation_button.clicked.connect(
                self._start_placeholder_separation
            )
            layout.addWidget(self.start_separation_button)

            self.file_status_label = create_status_label(qt, HIGHEST_APPROXIMATE_NOTICE)
            self.file_status_label.setObjectName("fileStatusLabel")
            layout.addWidget(self.file_status_label)
            layout.addStretch(1)
            return tab

        def _build_record_tab(self) -> object:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setSpacing(10)

            device_row = QtWidgets.QHBoxLayout()
            self.output_device_combo = QtWidgets.QComboBox()
            self.output_device_combo.setObjectName("outputDeviceSelector")
            self.output_device_combo.addItem("Default output device", "default")
            device_row.addWidget(
                create_labeled_row(qt, "Output device", self.output_device_combo),
                1,
            )
            self.refresh_devices_button = QtWidgets.QPushButton("Refresh Devices")
            self.refresh_devices_button.setObjectName("refreshDevicesButton")
            self.refresh_devices_button.clicked.connect(self._refresh_recording_devices)
            device_row.addWidget(self.refresh_devices_button)
            layout.addLayout(device_row)

            action_row = QtWidgets.QHBoxLayout()
            self.record_stop_button = QtWidgets.QPushButton("Record")
            self.record_stop_button.setObjectName("recordStopButton")
            self.record_stop_button.clicked.connect(self._toggle_placeholder_recording)
            action_row.addWidget(self.record_stop_button)

            self.elapsed_time_label = QtWidgets.QLabel(format_elapsed(0))
            self.elapsed_time_label.setObjectName("elapsedTimeLabel")
            action_row.addWidget(
                create_labeled_row(qt, "Elapsed", self.elapsed_time_label),
                1,
            )
            layout.addLayout(action_row)

            self.level_meter = QtWidgets.QProgressBar()
            self.level_meter.setObjectName("levelMeter")
            self.level_meter.setRange(0, 100)
            self.level_meter.setValue(0)
            self.level_meter.setTextVisible(False)
            layout.addWidget(create_labeled_row(qt, "Level", self.level_meter))

            self.send_recording_button = QtWidgets.QPushButton(
                "Send Recording To Separation"
            )
            self.send_recording_button.setObjectName("sendRecordingButton")
            self.send_recording_button.setEnabled(False)
            self.send_recording_button.clicked.connect(self._send_recording_placeholder)
            layout.addWidget(self.send_recording_button)

            self.record_status_label = create_status_label(qt, "Ready")
            self.record_status_label.setObjectName("recordStatusLabel")
            layout.addWidget(self.record_status_label)
            layout.addStretch(1)
            return tab

        def _build_jobs_tab(self) -> object:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setSpacing(10)

            self.jobs_list = QtWidgets.QListWidget()
            self.jobs_list.setObjectName("currentQueue")
            layout.addWidget(self.jobs_list, 1)

            self.progress_label = create_status_label(qt, "No active job")
            self.progress_label.setObjectName("progressText")
            layout.addWidget(create_labeled_row(qt, "Progress", self.progress_label))

            self.job_status_label = create_status_label(qt, "Idle")
            self.job_status_label.setObjectName("jobStatus")
            layout.addWidget(create_labeled_row(qt, "Status", self.job_status_label))

            self.open_output_folder_button = QtWidgets.QPushButton("Open Output Folder")
            self.open_output_folder_button.setObjectName("openOutputFolderButton")
            self.open_output_folder_button.clicked.connect(self._open_output_folder)
            layout.addWidget(self.open_output_folder_button)
            return tab

        def _build_settings_tab(self) -> object:
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setSpacing(10)

            root_row = QtWidgets.QHBoxLayout()
            self.output_root_edit = QtWidgets.QLineEdit(str(self.output_root))
            self.output_root_edit.setObjectName("outputRootSelector")
            root_row.addWidget(create_labeled_row(qt, "Output root", self.output_root_edit), 1)
            self.output_root_button = QtWidgets.QPushButton("Browse")
            self.output_root_button.setObjectName("outputRootBrowseButton")
            self.output_root_button.clicked.connect(self._choose_output_root)
            root_row.addWidget(self.output_root_button)
            layout.addLayout(root_row)

            self.ffmpeg_status_label = create_status_label(qt, "FFmpeg: not checked")
            self.ffmpeg_status_label.setObjectName("ffmpegStatus")
            layout.addWidget(self.ffmpeg_status_label)

            self.model_status_label = create_status_label(
                qt,
                "Model: htdemucs not loaded",
            )
            self.model_status_label.setObjectName("modelStatus")
            layout.addWidget(self.model_status_label)

            self.compute_status_label = create_status_label(
                qt,
                "CPU/GPU: auto selection not checked",
            )
            self.compute_status_label.setObjectName("computeStatus")
            layout.addWidget(self.compute_status_label)
            layout.addStretch(1)
            return tab

        def _choose_file(self) -> None:
            file_name, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Choose audio or video file",
                "",
                "Media files (*.wav *.flac *.mp3 *.m4a *.aac *.ogg *.mp4 *.mkv *.mov *.avi);;All files (*)",
            )
            if file_name:
                self._set_selected_file(Path(file_name))

        def _set_selected_file(self, path: Path) -> None:
            self.selected_file = Path(path)
            self.selected_file_label.setText(selected_file_summary(self.selected_file))
            self.file_status_label.setText(HIGHEST_APPROXIMATE_NOTICE)
            self._clear_error()

        def _start_placeholder_separation(self) -> None:
            if self.selected_file is None:
                self._show_error("Choose or drop a file before starting separation.")
                return

            output_format = combo_value(self.output_format_combo)
            device = combo_value(self.device_combo)
            self.jobs_list.addItem(f"{self.selected_file.name} - queued")
            self.progress_label.setText("Queued")
            self.job_status_label.setText("Preparing")
            self.tabs.setCurrentIndex(2)
            self._clear_error()

            worker = SeparationWorker(
                self.selected_file,
                output_format=output_format,
                device=device,
                use_qt_signals=True,
            )
            worker.signals.started.connect(self._handle_worker_started)
            worker.signals.progress.connect(self._handle_worker_progress)
            worker.signals.finished.connect(self._handle_worker_finished)
            worker.signals.failed.connect(self._handle_worker_failed)
            worker.queue()

            runnable = worker.as_qrunnable()
            self._active_workers.append(worker)
            self._active_runnables.append(runnable)
            QtCore.QThreadPool.globalInstance().start(runnable)

        def _handle_worker_started(self, worker_type: str) -> None:
            self.job_status_label.setText(f"{worker_type} running")

        def _handle_worker_progress(self, update: WorkerUpdate) -> None:
            if update.percent is None:
                self.progress_label.setText(update.message)
                return
            self.progress_label.setText(f"{update.message} ({update.percent}%)")

        def _handle_worker_finished(self, outcome: WorkerOutcome) -> None:
            self.job_status_label.setText("Complete")
            self.progress_label.setText(outcome.message)
            self.current_output_folder = self.output_root
            self.jobs_list.addItem("Placeholder separation complete")
            self.file_status_label.setText(HIGHEST_APPROXIMATE_NOTICE)

        def _handle_worker_failed(self, message: str) -> None:
            self.job_status_label.setText("Failed")
            self._show_error(message)

        def _refresh_recording_devices(self) -> None:
            self.output_device_combo.clear()
            self.output_device_combo.addItem("Default output device", "default")
            self.record_status_label.setText("Device list ready for recorder wiring")
            self._clear_error()

        def _toggle_placeholder_recording(self) -> None:
            if self._recording:
                self._recording = False
                self.record_timer.stop()
                self.level_meter.setValue(0)
                self.record_stop_button.setText("Record")
                self.record_status_label.setText("Stopped")
                self.send_recording_button.setEnabled(True)
                return

            self._recording = True
            self._record_elapsed_seconds = 0
            self.elapsed_time_label.setText(format_elapsed(0))
            self.level_meter.setValue(8)
            self.send_recording_button.setEnabled(False)
            self.record_stop_button.setText("Stop")
            self.record_status_label.setText("Recording")
            self.record_timer.start(1000)
            self._clear_error()

        def _tick_recording_timer(self) -> None:
            self._record_elapsed_seconds += 1
            self.elapsed_time_label.setText(format_elapsed(self._record_elapsed_seconds))
            self.level_meter.setValue(18 + (self._record_elapsed_seconds % 5) * 8)

        def _send_recording_placeholder(self) -> None:
            self.tabs.setCurrentIndex(0)
            self.file_status_label.setText(
                "Recording handoff will use the Step 9 pipeline. "
                + HIGHEST_APPROXIMATE_NOTICE
            )
            self._clear_error()

        def _choose_output_root(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Choose output root",
                str(self.output_root),
            )
            if not directory:
                return
            self.output_root = Path(directory)
            self.output_root_edit.setText(str(self.output_root))
            self._clear_error()

        def _open_output_folder(self) -> None:
            if self.current_output_folder is None:
                self._show_error("No output folder is available yet.")
                return
            if not self.current_output_folder.exists():
                self._show_error(f"Output folder does not exist: {self.current_output_folder}")
                return
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(str(self.current_output_folder))
            )

        def _show_error(self, message: str) -> None:
            self.global_error_label.setText(message)

        def _clear_error(self) -> None:
            self.global_error_label.setText("")

    return QtMainWindow


__all__ = [
    "DEVICE_OPTIONS",
    "HIGHEST_APPROXIMATE_NOTICE",
    "MAIN_WINDOW_TABS",
    "MainWindow",
    "OUTPUT_FORMAT_OPTIONS",
    "tab_by_key",
    "tab_titles",
]
