"""Background-capable GUI worker abstractions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from music_decomp.services.file_pipeline import FileSeparationPipeline

from .widgets import MissingPySide6Error, import_qt_core

WorkerOperation = Callable[[], object]


class WorkerState(str, Enum):
    """Lifecycle states shared by GUI workers."""

    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class WorkerUpdate:
    """Progress update emitted from a GUI worker."""

    stage: str
    message: str
    percent: int | None = None


@dataclass(frozen=True)
class WorkerOutcome:
    """Completion payload emitted from a GUI worker."""

    worker_type: str
    state: WorkerState
    message: str
    result: object | None = None


class FallbackSignal:
    """Tiny signal stand-in for tests and non-Qt imports."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., object]] = []

    def connect(self, callback: Callable[..., object]) -> None:
        """Register a callback for future emits."""
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        """Call all connected callbacks."""
        for callback in list(self._callbacks):
            callback(*args)


class FallbackWorkerSignals:
    """Signal hub used when PySide6 is absent or disabled for tests."""

    def __init__(self) -> None:
        self.started = FallbackSignal()
        self.progress = FallbackSignal()
        self.finished = FallbackSignal()
        self.failed = FallbackSignal()


class BaseGuiWorker:
    """Base worker with a testable lifecycle and optional Qt signal hub."""

    worker_type: ClassVar[str] = "worker"
    placeholder_message: ClassVar[str] = "Worker is ready for later pipeline wiring."

    def __init__(
        self,
        *,
        operation: WorkerOperation | None = None,
        description: str | None = None,
        use_qt_signals: bool = True,
    ) -> None:
        self.operation = operation
        self.description = description or self.placeholder_message
        self.state = WorkerState.IDLE
        self.error_message: str | None = None
        self.signals = _create_signal_hub(use_qt_signals=use_qt_signals)

    def queue(self) -> None:
        """Mark the worker as queued before a thread pool starts it."""
        self.state = WorkerState.QUEUED
        self.signals.progress.emit(
            WorkerUpdate(stage="queued", message=f"{self.worker_type} queued")
        )

    def run(self) -> WorkerOutcome:
        """Run the lightweight worker operation and emit lifecycle signals."""
        self.state = WorkerState.RUNNING
        self.signals.started.emit(self.worker_type)
        self.signals.progress.emit(
            WorkerUpdate(stage="running", message=self.description)
        )
        try:
            result = self._run_operation()
        except Exception as exc:  # pragma: no cover - defensive for GUI callbacks
            self.state = WorkerState.FAILED
            self.error_message = _worker_error_message(exc)
            self.signals.failed.emit(self.error_message)
            return WorkerOutcome(
                worker_type=self.worker_type,
                state=WorkerState.FAILED,
                message=self.error_message,
            )

        self.state = WorkerState.FINISHED
        outcome = WorkerOutcome(
            worker_type=self.worker_type,
            state=WorkerState.FINISHED,
            message=self._success_message(result),
            result=result,
        )
        self.signals.finished.emit(outcome)
        return outcome

    def as_qrunnable(self) -> object:
        """Return a QRunnable adapter when PySide6 is installed."""
        return create_qrunnable(self)

    def _run_operation(self) -> object:
        if self.operation is None:
            return {"status": "placeholder"}
        return self.operation()

    def _success_message(self, result: object) -> str:
        return self.placeholder_message


class MediaProbeWorker(BaseGuiWorker):
    """Worker for probing one local audio/video file."""

    worker_type = "media_probe"
    placeholder_message = "Media probe complete."

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        output_root: str | Path | None = None,
        output_format: str = "wav",
        device: str = "auto",
        operation: WorkerOperation | None = None,
        pipeline: object | None = None,
        use_qt_signals: bool = True,
    ) -> None:
        super().__init__(
            operation=operation,
            description="Probing media file.",
            use_qt_signals=use_qt_signals,
        )
        self.path = Path(path) if path is not None else None
        self.output_root = Path(output_root) if output_root is not None else None
        self.output_format = output_format
        self.device = device
        self.pipeline = pipeline

    def _run_operation(self) -> object:
        if self.operation is not None:
            return self.operation()
        if self.path is None:
            raise ValueError("No media file path was provided for probing.")
        pipeline = self.pipeline or FileSeparationPipeline()
        try:
            return pipeline.probe_input(self.path)  # type: ignore[attr-defined]
        except Exception as exc:
            record_probe_failure = getattr(pipeline, "record_probe_failure", None)
            if record_probe_failure is None:
                raise
            raise record_probe_failure(
                self.path,
                output_root=self.output_root,
                device=self.device,
                output_format=self.output_format,
                error_message=str(exc) or exc.__class__.__name__,
            ) from exc

    def _success_message(self, result: object) -> str:
        media_input = getattr(result, "media_input", None)
        kind = getattr(media_input, "kind", None)
        if isinstance(kind, str):
            return f"Media probe complete: {kind}"
        return self.placeholder_message


class RecordingWorker(BaseGuiWorker):
    """Shell worker for future recorder-service calls."""

    worker_type = "recording"
    placeholder_message = "Recording workflow will be wired in Step 9."

    def __init__(
        self,
        device_id: str | None = None,
        *,
        operation: WorkerOperation | None = None,
        use_qt_signals: bool = True,
    ) -> None:
        super().__init__(
            operation=operation,
            description="Preparing recording worker.",
            use_qt_signals=use_qt_signals,
        )
        self.device_id = device_id

    def _run_operation(self) -> object:
        if self.operation is not None:
            return self.operation()
        return {"device_id": self.device_id, "status": "recording-placeholder"}


class SeparationWorker(BaseGuiWorker):
    """Worker for running the local file separation pipeline."""

    worker_type = "separation"
    placeholder_message = "File separation complete; highest is approximate."

    def __init__(
        self,
        input_path: str | Path | None = None,
        *,
        output_root: str | Path | None = None,
        output_format: str = "wav",
        device: str = "auto",
        operation: WorkerOperation | None = None,
        pipeline: object | None = None,
        use_qt_signals: bool = True,
    ) -> None:
        super().__init__(
            operation=operation,
            description="Running file separation pipeline.",
            use_qt_signals=use_qt_signals,
        )
        self.input_path = Path(input_path) if input_path is not None else None
        self.output_root = Path(output_root) if output_root is not None else None
        self.output_format = output_format
        self.device = device
        self.pipeline = pipeline

    def _run_operation(self) -> object:
        if self.operation is not None:
            return self.operation()
        if self.input_path is None:
            raise ValueError("No input file path was provided for separation.")
        pipeline = self.pipeline or FileSeparationPipeline()
        return pipeline.run_file(  # type: ignore[attr-defined]
            self.input_path,
            output_root=self.output_root,
            output_format=self.output_format,
            device=self.device,
            progress_callback=self._emit_pipeline_progress,
        )

    def _emit_pipeline_progress(
        self,
        stage: str,
        message: str,
        percent: int | None,
    ) -> None:
        self.signals.progress.emit(
            WorkerUpdate(stage=stage, message=message, percent=percent)
        )

    def _success_message(self, result: object) -> str:
        output_dir = getattr(result, "output_dir", None)
        if output_dir is not None:
            return f"File separation complete: {output_dir}"
        return self.placeholder_message


def create_qrunnable(worker: BaseGuiWorker) -> object:
    """Wrap a worker in ``QThreadPool``-compatible ``QRunnable``."""
    qt_core = import_qt_core()

    class WorkerRunnable(qt_core.QRunnable):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__()
            self.worker = worker

        def run(self) -> None:  # noqa: D401, N802 - Qt override
            """Run the wrapped worker."""
            self.worker.run()

    return WorkerRunnable()


def _create_signal_hub(*, use_qt_signals: bool) -> object:
    if not use_qt_signals:
        return FallbackWorkerSignals()
    try:
        qt_core = import_qt_core()
    except MissingPySide6Error:
        return FallbackWorkerSignals()

    class QtWorkerSignals(qt_core.QObject):  # type: ignore[misc, valid-type]
        started = qt_core.Signal(str)
        progress = qt_core.Signal(object)
        finished = qt_core.Signal(object)
        failed = qt_core.Signal(str)

    return QtWorkerSignals()


def _worker_error_message(exc: BaseException) -> str:
    message = str(exc) or exc.__class__.__name__
    log_path = getattr(exc, "log_path", None)
    if log_path is not None:
        return f"{message}\nLog: {log_path}"
    output_dir = getattr(exc, "output_dir", None)
    if output_dir is not None:
        return f"{message}\nOutput: {output_dir}"
    return message
