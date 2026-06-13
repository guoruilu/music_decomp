"""Small GUI helper types and lazy Qt widget factories."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PYSIDE6_INSTALL_MESSAGE = (
    "PySide6 is not installed. Install the optional GUI dependencies with "
    "`python -m pip install 'music-decomp[gui]'`."
)


class MissingPySide6Error(ImportError):
    """Raised when a GUI object is requested without PySide6 installed."""


@dataclass(frozen=True)
class QtModules:
    """Container for lazily imported PySide6 modules."""

    QtCore: Any
    QtGui: Any
    QtWidgets: Any


@dataclass(frozen=True)
class OptionSpec:
    """Stable option metadata for combo boxes and tests."""

    label: str
    value: str


@dataclass(frozen=True)
class ControlSpec:
    """Stable control metadata for the GUI shell."""

    key: str
    label: str
    control_type: str
    options: tuple[OptionSpec, ...] = ()


@dataclass(frozen=True)
class TabSpec:
    """Stable tab metadata for the GUI shell."""

    key: str
    title: str
    controls: tuple[ControlSpec, ...]


def import_qt_modules() -> QtModules:
    """Import PySide6 modules on demand."""
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as exc:
        raise MissingPySide6Error(PYSIDE6_INSTALL_MESSAGE) from exc
    return QtModules(QtCore=QtCore, QtGui=QtGui, QtWidgets=QtWidgets)


def import_qt_core() -> Any:
    """Import ``PySide6.QtCore`` on demand."""
    try:
        from PySide6 import QtCore
    except ImportError as exc:
        raise MissingPySide6Error(PYSIDE6_INSTALL_MESSAGE) from exc
    return QtCore


def populate_combo_box(combo_box: Any, options: Iterable[OptionSpec]) -> None:
    """Populate a Qt combo box from stable option specs."""
    combo_box.clear()
    for option in options:
        combo_box.addItem(option.label, option.value)


def combo_value(combo_box: Any) -> str:
    """Return the selected value from a Qt combo box."""
    value = combo_box.currentData()
    if value is None:
        return combo_box.currentText().strip().lower()
    return str(value)


def create_labeled_row(qt: QtModules, label: str, widget: Any) -> Any:
    """Create a compact row with a text label and one control."""
    row = qt.QtWidgets.QWidget()
    layout = qt.QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    label_widget = qt.QtWidgets.QLabel(label)
    label_widget.setMinimumWidth(120)
    layout.addWidget(label_widget)
    layout.addWidget(widget, 1)
    return row


def create_status_label(qt: QtModules, text: str = "") -> Any:
    """Create a word-wrapped status label for visible GUI feedback."""
    label = qt.QtWidgets.QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(_text_selectable_flag(qt))
    return label


def create_drop_zone(qt: QtModules, on_file_selected: Callable[[Path], None]) -> Any:
    """Create a drag/drop target that reports the first local file path."""

    class DropZone(qt.QtWidgets.QLabel):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__("Drop audio or video file here")
            self.setObjectName("fileDropZone")
            self.setAcceptDrops(True)
            self.setMinimumHeight(88)
            self.setAlignment(_align_center(qt))
            self.setFrameShape(qt.QtWidgets.QFrame.Shape.StyledPanel)
            self.setStyleSheet(
                "QLabel#fileDropZone { border: 1px dashed #68707d; padding: 16px; }"
            )

        def dragEnterEvent(self, event: Any) -> None:  # noqa: N802 - Qt override
            if _first_local_file(event.mimeData()) is None:
                event.ignore()
                return
            event.acceptProposedAction()

        def dropEvent(self, event: Any) -> None:  # noqa: N802 - Qt override
            path = _first_local_file(event.mimeData())
            if path is None:
                event.ignore()
                return
            on_file_selected(path)
            event.acceptProposedAction()

    return DropZone()


def selected_file_summary(path: str | Path) -> str:
    """Return compact selected-file details for the shell."""
    file_path = Path(path)
    try:
        size_text = _format_bytes(file_path.stat().st_size)
    except OSError:
        size_text = "size unavailable"
    return f"{file_path.name}\n{file_path}\n{size_text}"


def format_elapsed(seconds: float) -> str:
    """Format elapsed recording time as HH:MM:SS."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _first_local_file(mime_data: Any) -> Path | None:
    if mime_data is None or not mime_data.hasUrls():
        return None
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        return Path(url.toLocalFile())
    return None


def _format_bytes(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _align_center(qt: QtModules) -> Any:
    try:
        return qt.QtCore.Qt.AlignmentFlag.AlignCenter
    except AttributeError:  # pragma: no cover - older Qt compatibility
        return qt.QtCore.Qt.AlignCenter


def _text_selectable_flag(qt: QtModules) -> Any:
    try:
        return qt.QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
    except AttributeError:  # pragma: no cover - older Qt compatibility
        return qt.QtCore.Qt.TextSelectableByMouse
