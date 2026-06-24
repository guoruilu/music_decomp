"""Verify a Windows PyInstaller portable package for Music Decomp."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import wave
from collections.abc import Iterable, Sequence


DEFAULT_TIMEOUT_SECONDS = 30
TEXT_SCAN_SUFFIXES = {".bat", ".cmd", ".cfg", ".ini", ".json", ".ps1", ".pth", ".txt"}


class VerificationError(RuntimeError):
    """Raised when a portable package check fails."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        verify_package(
            package_dir=args.package_dir,
            timeout_seconds=args.timeout_seconds,
            keep_path=args.keep_path,
            structure_only=args.structure_only,
            skip_ffmpeg_resolution_smoke=args.skip_ffmpeg_resolution_smoke,
        )
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the MusicDecomp PyInstaller one-folder package."
    )
    parser.add_argument(
        "--package-dir",
        required=True,
        type=Path,
        help="Path to dist/MusicDecomp.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout for packaged executable smoke commands.",
    )
    parser.add_argument(
        "--keep-path",
        action="store_true",
        help="Do not isolate PATH while running packaged executable checks.",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Check package files only; do not run Windows executables.",
    )
    parser.add_argument(
        "--skip-ffmpeg-resolution-smoke",
        action="store_true",
        help="Skip bundled FFprobe executable and packaged probe smoke checks.",
    )
    return parser


def verify_package(
    *,
    package_dir: Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    keep_path: bool = False,
    structure_only: bool = False,
    skip_ffmpeg_resolution_smoke: bool = False,
) -> None:
    package_dir = package_dir.resolve()
    if timeout_seconds <= 0:
        raise VerificationError("--timeout-seconds must be positive.")
    if not package_dir.is_dir():
        raise VerificationError(f"Package directory does not exist: {package_dir}")

    gui_exe = _require_file(package_dir / "MusicDecomp.exe", "GUI executable")
    cli_exe = _require_file(package_dir / "music-decomp.exe", "CLI executable")
    ffmpeg = _require_resource(package_dir, Path("vendor/ffmpeg/bin/ffmpeg.exe"), "FFmpeg")
    ffprobe = _require_resource(
        package_dir,
        Path("vendor/ffmpeg/bin/ffprobe.exe"),
        "FFprobe",
    )
    model_manifest = _require_resource(
        package_dir,
        Path("models/manifest.json"),
        "model manifest",
    )
    _require_resource(
        package_dir,
        Path("manifests/dependency-and-asset-manifest.md"),
        "dependency manifest",
    )
    _require_any_license_file(package_dir)
    _validate_model_manifest(model_manifest)
    _check_no_source_venv_launch_references(package_dir)

    print(f"OK: package directory exists: {package_dir}")
    print(f"OK: GUI executable exists: {gui_exe}")
    print(f"OK: CLI executable exists: {cli_exe}")
    print(f"OK: bundled FFmpeg exists: {ffmpeg}")
    print(f"OK: bundled FFprobe exists: {ffprobe}")
    print(f"OK: model manifest exists: {model_manifest}")

    if structure_only:
        print("STRUCTURE ONLY: executable smoke checks were skipped.")
        return

    if platform.system().lower() != "windows":
        raise VerificationError(
            "Running the packaged Windows executables requires Windows. "
            "Use --structure-only only for non-Windows structural checks."
        )

    env = _portable_env(package_dir, keep_path=keep_path)
    version_result = _run_package_command(
        [cli_exe, "--version"],
        package_dir=package_dir,
        env=env,
        timeout_seconds=timeout_seconds,
        description="music-decomp --version",
    )
    version_text = (version_result.stdout + version_result.stderr).strip()
    if "music-decomp" not in version_text.lower():
        raise VerificationError(
            "music-decomp --version did not print the expected application name."
        )
    print(f"OK: music-decomp --version works: {version_text}")

    if not skip_ffmpeg_resolution_smoke:
        _run_bundled_ffprobe_smoke(
            ffprobe=ffprobe,
            cli_exe=cli_exe,
            package_dir=package_dir,
            env=env,
            timeout_seconds=timeout_seconds,
        )
        print("OK: packaged app resolves bundled FFprobe without system PATH.")

    print("OK: executable checks ran without PYTHONPATH, VIRTUAL_ENV, or source .venv PATH.")


def _resource_roots(package_dir: Path) -> tuple[Path, ...]:
    return (package_dir / "_internal", package_dir)


def _require_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise VerificationError(f"{description} is missing: {path}")
    return path


def _require_resource(package_dir: Path, relative_path: Path, description: str) -> Path:
    for root in _resource_roots(package_dir):
        candidate = root / relative_path
        if candidate.is_file():
            return candidate
    checked = ", ".join(str(root / relative_path) for root in _resource_roots(package_dir))
    raise VerificationError(f"{description} is missing; checked {checked}")


def _license_like_files(package_dir: Path) -> Iterable[Path]:
    for root in _resource_roots(package_dir):
        for base in (root / "licenses", root / "vendor" / "ffmpeg"):
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.name.lower().startswith(
                    ("license", "copying", "notice")
                ):
                    yield path


def _require_any_license_file(package_dir: Path) -> None:
    if next(iter(_license_like_files(package_dir)), None) is None:
        raise VerificationError(
            "No bundled license, copying, or notice files were found in the package."
        )


def _validate_model_manifest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"Model manifest is not valid JSON: {path}") from exc
    if not isinstance(payload, dict) or not payload:
        raise VerificationError(f"Model manifest must be a non-empty JSON object: {path}")


def _check_no_source_venv_launch_references(package_dir: Path) -> None:
    for path in package_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SCAN_SUFFIXES:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        normalized = text.replace("\\", "/").lower()
        if "/.venv/" in normalized or ".venv/scripts/python" in normalized:
            raise VerificationError(f"Launch/config file references a source .venv: {path}")


def _portable_env(package_dir: Path, *, keep_path: bool) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "MUSIC_DECOMP_FFMPEG",
        "MUSIC_DECOMP_FFPROBE",
    ):
        env.pop(key, None)

    if keep_path:
        return env

    path_entries = [
        package_dir,
        package_dir / "_internal",
        package_dir / "vendor" / "ffmpeg" / "bin",
        package_dir / "_internal" / "vendor" / "ffmpeg" / "bin",
    ]
    system_root = os.environ.get("SystemRoot")
    if system_root:
        path_entries.extend([Path(system_root) / "System32", Path(system_root)])
    env["PATH"] = os.pathsep.join(str(path) for path in path_entries if path.exists())
    return env


def _run_package_command(
    command: Sequence[Path | str],
    *,
    package_dir: Path,
    env: dict[str, str],
    timeout_seconds: int,
    description: str,
    require_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            [str(part) for part in command],
            cwd=package_dir,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VerificationError(f"{description} timed out after {timeout_seconds}s.") from exc

    if completed.returncode != 0:
        raise VerificationError(
            f"{description} failed with exit code {completed.returncode}.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    if require_output and not (completed.stdout or completed.stderr):
        raise VerificationError(f"{description} produced no output.")
    return completed


def _run_bundled_ffprobe_smoke(
    *,
    ffprobe: Path,
    cli_exe: Path,
    package_dir: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> None:
    ffprobe_result = _run_package_command(
        [ffprobe, "-version"],
        package_dir=package_dir,
        env=env,
        timeout_seconds=timeout_seconds,
        description="bundled ffprobe -version",
    )
    ffprobe_output = ffprobe_result.stdout + ffprobe_result.stderr
    if "ffprobe" not in ffprobe_output.lower():
        raise VerificationError("Bundled ffprobe -version output did not identify FFprobe.")

    with tempfile.TemporaryDirectory(prefix="music-decomp-verify-") as temp_dir:
        fixture_path = Path(temp_dir) / "tiny.wav"
        _write_tiny_wav(fixture_path)
        probe_result = _run_package_command(
            [cli_exe, "probe", fixture_path],
            package_dir=package_dir,
            env=env,
            timeout_seconds=timeout_seconds,
            description="music-decomp probe tiny WAV",
        )

    try:
        payload = json.loads(probe_result.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(
            "music-decomp probe did not return valid JSON for the tiny WAV fixture."
        ) from exc

    if payload.get("kind") != "audio":
        raise VerificationError(
            "music-decomp probe did not identify the tiny WAV fixture as audio."
        )


def _write_tiny_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * 441)


if __name__ == "__main__":
    raise SystemExit(main())
