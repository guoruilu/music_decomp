"""Application entry points."""

from __future__ import annotations

import sys
from collections.abc import Sequence

GUI_EXTRA_INSTALL_HINT = (
    "PySide6 is not installed. Install the optional GUI dependencies with "
    "`python -m pip install 'music-decomp[gui]'`."
)


class MissingGuiDependencyError(RuntimeError):
    """Raised when the optional GUI dependency set is unavailable."""


def run_gui(argv: Sequence[str] | None = None) -> int:
    """Launch the desktop GUI, importing PySide6 only on this code path."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise MissingGuiDependencyError(GUI_EXTRA_INSTALL_HINT) from exc

    from music_decomp.ui.main_window import MainWindow
    from music_decomp.ui.widgets import MissingPySide6Error

    app_args = list(argv) if argv is not None else sys.argv
    qt_app = QApplication.instance() or QApplication(app_args)
    try:
        window = MainWindow()
    except MissingPySide6Error as exc:
        raise MissingGuiDependencyError(GUI_EXTRA_INSTALL_HINT) from exc

    window.show()
    return int(qt_app.exec())


def run() -> int:
    """Run the desktop GUI application."""
    return run_gui()
