from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from music_decomp import config
from music_decomp.config import MissingExecutableError
from music_decomp.services.media_service import MediaService
from music_decomp.utils import subprocesses
from music_decomp.utils.subprocesses import CommandExecutionError


FIXTURES = Path(__file__).parent / "fixtures"


def _completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def test_resolve_ffmpeg_path_prefers_environment_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_ffmpeg = tmp_path / "env" / "ffmpeg.exe"
    bundled_ffmpeg = tmp_path / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe"
    env_ffmpeg.parent.mkdir(parents=True)
    bundled_ffmpeg.parent.mkdir(parents=True)
    env_ffmpeg.write_text("", encoding="utf-8")
    bundled_ffmpeg.write_text("", encoding="utf-8")
    monkeypatch.setenv("MUSIC_DECOMP_FFMPEG", str(env_ffmpeg))
    monkeypatch.setattr(config, "resource_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(config.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    assert config.resolve_ffmpeg_path() == env_ffmpeg


def test_resolve_ffprobe_path_uses_bundled_before_system(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundled_ffprobe = tmp_path / "vendor" / "ffmpeg" / "bin" / "ffprobe.exe"
    bundled_ffprobe.parent.mkdir(parents=True)
    bundled_ffprobe.write_text("", encoding="utf-8")
    monkeypatch.delenv("MUSIC_DECOMP_FFPROBE", raising=False)
    monkeypatch.setattr(config, "resource_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(config.shutil, "which", lambda name: "/usr/bin/ffprobe")

    assert config.resolve_ffprobe_path() == bundled_ffprobe


def test_system_ffmpeg_is_only_allowed_in_development_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("MUSIC_DECOMP_FFMPEG", raising=False)
    monkeypatch.setattr(config, "resource_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(config.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(config, "is_frozen", lambda: False)

    assert config.resolve_ffmpeg_path() == Path("/usr/bin/ffmpeg")

    monkeypatch.setattr(config, "is_frozen", lambda: True)
    with pytest.raises(MissingExecutableError, match="Unable to find ffmpeg"):
        config.resolve_ffmpeg_path()


def test_missing_ffmpeg_path_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("MUSIC_DECOMP_FFMPEG", raising=False)
    monkeypatch.setattr(config, "resource_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(config.shutil, "which", lambda name: None)
    monkeypatch.setattr(config, "is_frozen", lambda: False)

    with pytest.raises(MissingExecutableError) as exc_info:
        config.resolve_ffmpeg_path()

    message = str(exc_info.value)
    assert "ffmpeg" in message
    assert "MUSIC_DECOMP_FFMPEG" in message


def test_missing_ffprobe_path_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("MUSIC_DECOMP_FFPROBE", raising=False)
    monkeypatch.setattr(config, "resource_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(config.shutil, "which", lambda name: None)
    monkeypatch.setattr(config, "is_frozen", lambda: False)

    with pytest.raises(MissingExecutableError) as exc_info:
        config.resolve_ffprobe_path()

    message = str(exc_info.value)
    assert "ffprobe" in message
    assert "MUSIC_DECOMP_FFPROBE" in message


def test_probe_builds_ffprobe_json_command_and_parses_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture_json = (FIXTURES / "ffprobe_audio.json").read_text(encoding="utf-8")
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed(fixture_json)

    monkeypatch.setattr("music_decomp.services.media_service.run_command", fake_run_command)
    service = MediaService(
        ffmpeg_path=tmp_path / "ffmpeg.exe",
        ffprobe_path=tmp_path / "ffprobe.exe",
    )
    input_path = tmp_path / "song.wav"

    data = service.probe(input_path)

    assert data["format"]["duration"] == "12.345"
    assert calls == [
        [
            tmp_path / "ffprobe.exe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            input_path,
        ]
    ]
    assert isinstance(calls[0], list)


def test_extract_audio_builds_stereo_44100_wav_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed()

    monkeypatch.setattr("music_decomp.services.media_service.run_command", fake_run_command)
    service = MediaService(
        ffmpeg_path=tmp_path / "ffmpeg.exe",
        ffprobe_path=tmp_path / "ffprobe.exe",
    )
    input_path = tmp_path / "clip.mp4"
    output_path = tmp_path / "audio" / "input.wav"

    assert service.extract_audio(input_path, output_path) == output_path

    assert calls == [
        [
            tmp_path / "ffmpeg.exe",
            "-y",
            "-i",
            input_path,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-sample_fmt",
            "s16",
            output_path,
        ]
    ]


def test_detect_kind_returns_audio_for_audio_only_streams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture_json = (FIXTURES / "ffprobe_audio.json").read_text(encoding="utf-8")
    monkeypatch.setattr(
        "music_decomp.services.media_service.run_command",
        lambda args: _completed(fixture_json),
    )
    service = MediaService(
        ffmpeg_path=tmp_path / "ffmpeg.exe",
        ffprobe_path=tmp_path / "ffprobe.exe",
    )

    assert service.detect_kind(tmp_path / "song.wav") == "audio"


def test_detect_kind_returns_video_when_video_stream_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture_json = (FIXTURES / "ffprobe_video.json").read_text(encoding="utf-8")
    monkeypatch.setattr(
        "music_decomp.services.media_service.run_command",
        lambda args: _completed(fixture_json),
    )
    service = MediaService(
        ffmpeg_path=tmp_path / "ffmpeg.exe",
        ffprobe_path=tmp_path / "ffprobe.exe",
    )

    assert service.detect_kind(tmp_path / "clip.mp4") == "video"


def test_run_command_rejects_shell_string() -> None:
    with pytest.raises(TypeError, match="not a shell string"):
        subprocesses.run_command("ffmpeg -version")  # type: ignore[arg-type]


def test_command_error_message_includes_executable_exit_code_and_stderr_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["/tools/ffmpeg.exe"],
            returncode=17,
            stdout="",
            stderr="x" * 5000,
        )

    monkeypatch.setattr(subprocesses.subprocess, "run", fake_run)

    with pytest.raises(CommandExecutionError) as exc_info:
        subprocesses.run_command(["/tools/ffmpeg.exe", "-version"])

    message = str(exc_info.value)
    assert "/tools/ffmpeg.exe" in message
    assert "exit code: 17" in message
    assert "stderr tail:" in message
    assert "x" * 4000 in message
