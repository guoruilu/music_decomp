"""GUI shell package with lazy PySide6 imports."""

from .main_window import (
    HIGHEST_APPROXIMATE_NOTICE,
    MAIN_WINDOW_TABS,
    MainWindow,
    tab_by_key,
    tab_titles,
)
from .workers import (
    MediaProbeWorker,
    RecordingWorker,
    SeparationWorker,
    WorkerOutcome,
    WorkerState,
    WorkerUpdate,
)

__all__ = [
    "HIGHEST_APPROXIMATE_NOTICE",
    "MAIN_WINDOW_TABS",
    "MainWindow",
    "MediaProbeWorker",
    "RecordingWorker",
    "SeparationWorker",
    "WorkerOutcome",
    "WorkerState",
    "WorkerUpdate",
    "tab_by_key",
    "tab_titles",
]
