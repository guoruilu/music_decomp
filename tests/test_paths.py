from __future__ import annotations

import sys
from pathlib import Path

import pytest

from music_decomp.paths import app_data_dir, is_frozen, project_root, resource_path


def test_project_root_points_to_repository_root() -> None:
    root = project_root()

    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "music_decomp").is_dir()


def test_app_data_dir_uses_xdg_data_home_on_non_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert app_data_dir() == tmp_path / "MusicDecomp"


def test_app_data_dir_uses_local_app_data_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert app_data_dir() == tmp_path / "MusicDecomp"


def test_resource_path_resolves_from_project_root_in_source_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    assert resource_path("README.md") == project_root() / "README.md"


def test_resource_path_resolves_from_pyinstaller_meipass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert is_frozen()
    assert resource_path(Path("assets/icon.png")) == tmp_path / "assets" / "icon.png"


def test_resource_path_rejects_absolute_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expects a relative path"):
        resource_path(tmp_path)
