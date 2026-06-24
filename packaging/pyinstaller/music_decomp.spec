# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-folder build spec for the Windows portable package."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata


SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parents[1]
SRC_DIR = PROJECT_ROOT / "src"
BUILD_ENTRY_DIR = PROJECT_ROOT / "build" / "pyinstaller-entry"
ENTRY_SCRIPT = BUILD_ENTRY_DIR / "music_decomp_packaged_entry.py"

VENDOR_FFMPEG_DIR = PROJECT_ROOT / "vendor" / "ffmpeg"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_MANIFEST = MODELS_DIR / "manifest.json"
DEPENDENCY_MANIFEST = (
    PROJECT_ROOT / "docs" / "by-feature" / "dependency-and-asset-manifest.md"
)

REQUIRED_RESOURCE_FILES = (
    VENDOR_FFMPEG_DIR / "bin" / "ffmpeg.exe",
    VENDOR_FFMPEG_DIR / "bin" / "ffprobe.exe",
    MODEL_MANIFEST,
)
REQUIRED_IMPORT_PACKAGES = (
    "PySide6",
    "demucs",
    "torch",
    "torchaudio",
    "numpy",
    "soundcard",
)
METADATA_DISTRIBUTIONS = (
    "music-decomp",
    "PySide6",
    "demucs",
    "torch",
    "torchaudio",
    "numpy",
    "SoundCard",
)


def _write_packaged_entry() -> None:
    """Create a build-local entry point used only by PyInstaller."""
    BUILD_ENTRY_DIR.mkdir(parents=True, exist_ok=True)
    ENTRY_SCRIPT.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "import sys",
                "from pathlib import Path",
                "",
                "from music_decomp import cli",
                "from music_decomp.app import run_gui",
                "",
                "",
                "def main() -> int:",
                "    executable_name = Path(sys.argv[0]).stem.lower()",
                "    if executable_name == 'music-decomp':",
                "        return cli.main(sys.argv[1:])",
                "    return run_gui(argv=['MusicDecomp'])",
                "",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "",
            )
        ),
        encoding="utf-8",
    )


def _assert_packaging_prerequisites() -> None:
    missing_files = [path for path in REQUIRED_RESOURCE_FILES if not path.is_file()]
    if missing_files:
        formatted = "\n".join(f"  - {path}" for path in missing_files)
        raise RuntimeError(
            "Required portable-package resource files are missing:\n" + formatted
        )

    model_payload_files = [
        path
        for path in MODELS_DIR.rglob("*")
        if path.is_file() and path != MODEL_MANIFEST
    ]
    if not model_payload_files:
        raise RuntimeError("No model payload files were found under models/.")

    if not _license_like_files(VENDOR_FFMPEG_DIR):
        raise RuntimeError(
            "No FFmpeg license, copying, or notice files were found under vendor/ffmpeg/."
        )

    missing_packages = [
        package for package in REQUIRED_IMPORT_PACKAGES if find_spec(package) is None
    ]
    if missing_packages:
        formatted = ", ".join(missing_packages)
        raise RuntimeError(
            "Required Python packages are not importable for packaging: " + formatted
        )


def _license_like_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    names = ("license", "copying", "notice")
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name.lower().startswith(names)
    ]


def _collect_project_datas() -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = [
        (str(VENDOR_FFMPEG_DIR), "vendor/ffmpeg"),
        (str(MODELS_DIR), "models"),
        (str(DEPENDENCY_MANIFEST), "manifests"),
        (str(PROJECT_ROOT / "requirements" / "base.in"), "manifests/requirements"),
        (str(PROJECT_ROOT / "requirements" / "win-cpu.txt"), "manifests/requirements"),
        (str(PROJECT_ROOT / "requirements" / "win-cuda.txt"), "manifests/requirements"),
    ]

    vendor_readme = PROJECT_ROOT / "vendor" / "README.md"
    if vendor_readme.is_file():
        datas.append((str(vendor_readme), "manifests/vendor"))

    for pattern in ("LICENSE*", "NOTICE*", "COPYING*", "THIRD_PARTY*"):
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_file():
                datas.append((str(path), "licenses/project"))

    for path in _license_like_files(VENDOR_FFMPEG_DIR):
        relative_parent = path.parent.relative_to(VENDOR_FFMPEG_DIR)
        datas.append((str(path), str(Path("licenses") / "ffmpeg" / relative_parent)))

    return datas


def _collect_runtime_dependencies() -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    datas: list[tuple[str, str]] = []
    binaries: list[tuple[str, str]] = []
    hiddenimports: list[str] = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "demucs.api",
        "soundcard",
        "torch",
        "torchaudio",
    ]

    for package_name in REQUIRED_IMPORT_PACKAGES:
        package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
        datas.extend(package_datas)
        binaries.extend(package_binaries)
        hiddenimports.extend(package_hiddenimports)

    for distribution_name in METADATA_DISTRIBUTIONS:
        try:
            datas.extend(copy_metadata(distribution_name, recursive=True))
        except Exception as exc:
            print(f"metadata copy skipped for {distribution_name}: {exc}")

    return datas, binaries, hiddenimports


_assert_packaging_prerequisites()
_write_packaged_entry()

project_datas = _collect_project_datas()
dependency_datas, dependency_binaries, dependency_hiddenimports = (
    _collect_runtime_dependencies()
)

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR), str(PROJECT_ROOT)],
    binaries=dependency_binaries,
    datas=project_datas + dependency_datas,
    hiddenimports=dependency_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

gui_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MusicDecomp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

cli_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="music-decomp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    gui_exe,
    cli_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MusicDecomp",
)
