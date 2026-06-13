from __future__ import annotations

import math
import os
import subprocess
import wave
from pathlib import Path

import pytest

from music_decomp.domain import MediaInput
from music_decomp.services.export_service import ExportService
from music_decomp.services import separation_service
from music_decomp.services.separation_service import (
    DemucsSeparatorBackend,
    HIGHEST_FILTER,
    LOWEST_FILTER,
    SeparationError,
    SeparationDeviceError,
    SeparationService,
    clear_separator_cache,
)


def _write_synthetic_mix(path: Path) -> Path:
    """Write a tiny 120 Hz + 4000 Hz stereo WAV using only the stdlib."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    frames = int(sample_rate * 0.05)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            t = index / sample_rate
            sample = 0.25 * math.sin(2 * math.pi * 120 * t)
            sample += 0.20 * math.sin(2 * math.pi * 4000 * t)
            value = int(max(-1.0, min(1.0, sample)) * 32767)
            frame = value.to_bytes(2, byteorder="little", signed=True) * 2
            wav.writeframesraw(frame)
    return path


def _media(tmp_path: Path) -> MediaInput:
    return MediaInput(
        kind="audio",
        path=tmp_path / "input.wav",
        title="synthetic",
        duration_seconds=0.05,
        sample_rate=44100,
    )


def _job_result(tmp_path: Path, *, stems: tuple[str, ...] | None = None):
    return ExportService(output_root=tmp_path).prepare_job(
        _media(tmp_path),
        stems=stems or ("vocals", "drums", "bass", "other", "lowest", "highest"),
    )


class FakeBackend:
    def __init__(
        self,
        model_name: str,
        device: str,
        *,
        fail: bool = False,
        include_bass: bool = True,
        calls: list[tuple[str, str]] | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.fail = fail
        self.include_bass = include_bass
        self.calls = calls
        if self.calls is not None:
            self.calls.append((model_name, device))

    def separate_to_wav(self, mixture_wav: Path, output_dir: Path) -> dict[str, Path]:
        if self.fail:
            raise RuntimeError(f"{self.device} backend failed")
        output_dir.mkdir(parents=True, exist_ok=True)
        stems = ["vocals", "drums", "other"]
        if self.include_bass:
            stems.append("bass")
        outputs = {}
        for stem in stems:
            path = output_dir / f"{stem}.wav"
            path.write_bytes(f"{stem} from {mixture_wav.name}".encode("utf-8"))
            outputs[stem] = path
        return outputs


def test_device_resolution_cpu_cuda_and_auto(tmp_path: Path) -> None:
    service_no_cuda = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        cuda_available=lambda: False,
    )
    assert service_no_cuda.resolve_device("cpu") == "cpu"
    assert service_no_cuda.resolve_device("auto") == "cpu"
    with pytest.raises(SeparationDeviceError, match="CUDA was requested"):
        service_no_cuda.resolve_device("cuda")

    service_with_cuda = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        cuda_available=lambda: True,
    )
    assert service_with_cuda.resolve_device("auto") == "cuda"
    assert service_with_cuda.resolve_device("cuda") == "cuda"


def test_success_progress_sequence_and_lowest_highest_derivation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        Path(args[-1]).write_bytes(b"filtered wav")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(separation_service, "run_command", fake_run_command)
    result = _job_result(tmp_path)
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    progress: list[str] = []
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=lambda model, device: FakeBackend(model, device),
        cuda_available=lambda: False,
    )

    run_result = service.separate(result, mixture, progress.append)

    assert progress == ["preparing", "loading_model", "separating", "exporting", "done"]
    assert run_result.actual_device == "cpu"
    assert set(run_result.output_files) == {
        "vocals",
        "drums",
        "bass",
        "other",
        "lowest",
        "highest",
    }
    for path in run_result.output_files.values():
        assert path.is_file()
    assert run_result.stem_info["lowest"].source == "bass_copy"
    assert run_result.stem_info["lowest"].approximate is False
    assert run_result.stem_info["highest"].source == "mixture_highpass_band"
    assert run_result.highest_is_approximate is True
    assert calls == [
        [
            tmp_path / "ffmpeg",
            "-y",
            "-i",
            mixture,
            "-af",
            HIGHEST_FILTER,
            "-ac",
            "2",
            "-ar",
            "44100",
            "-sample_fmt",
            "s16",
            result.job.output_dir / "_intermediate" / "derived" / "highest.wav",
        ]
    ]


def test_lowest_falls_back_to_mixture_lowpass_when_bass_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        Path(args[-1]).write_bytes(b"filtered wav")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(separation_service, "run_command", fake_run_command)
    result = _job_result(tmp_path, stems=("lowest", "highest"))
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=lambda model, device: FakeBackend(
            model,
            device,
            include_bass=False,
        ),
        cuda_available=lambda: False,
    )

    run_result = service.separate(result, mixture)

    assert run_result.stem_info["lowest"].source == "mixture_lowpass"
    assert run_result.stem_info["lowest"].approximate is True
    filters = [call[call.index("-af") + 1] for call in calls]
    assert filters == [LOWEST_FILTER, HIGHEST_FILTER]


def test_missing_requested_bass_fails_instead_of_using_lowest_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(separation_service, "run_command", fake_run_command)
    result = _job_result(tmp_path, stems=("bass", "lowest"))
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    progress: list[str] = []
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=lambda model, device: FakeBackend(
            model,
            device,
            include_bass=False,
        ),
        cuda_available=lambda: False,
    )

    with pytest.raises(SeparationError, match="required stem: bass"):
        service.separate(result, mixture, progress.append)

    assert progress == ["preparing", "loading_model", "separating", "exporting", "failed"]
    assert calls == []
    assert not result.output_files["lowest"].exists()


def test_requested_non_wav_format_converts_raw_and_derived_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[object]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        Path(args[-1]).write_bytes(b"converted or filtered")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(separation_service, "run_command", fake_run_command)
    result = ExportService(output_root=tmp_path).prepare_job(
        _media(tmp_path),
        output_format="flac",
        stems=("bass", "lowest", "highest"),
    )
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=lambda model, device: FakeBackend(model, device),
        cuda_available=lambda: False,
    )

    run_result = service.separate(result, mixture)

    assert {path.suffix for path in run_result.output_files.values()} == {".flac"}
    assert calls == [
        [
            tmp_path / "ffmpeg",
            "-y",
            "-i",
            result.job.output_dir / "_intermediate" / "demucs" / "bass.wav",
            result.output_files["bass"],
        ],
        [
            tmp_path / "ffmpeg",
            "-y",
            "-i",
            result.job.output_dir / "_intermediate" / "demucs" / "bass.wav",
            result.output_files["lowest"],
        ],
        [
            tmp_path / "ffmpeg",
            "-y",
            "-i",
            mixture,
            "-af",
            HIGHEST_FILTER,
            "-ac",
            "2",
            "-ar",
            "44100",
            "-sample_fmt",
            "s16",
            result.job.output_dir / "_intermediate" / "derived" / "highest.wav",
        ],
        [
            tmp_path / "ffmpeg",
            "-y",
            "-i",
            result.job.output_dir / "_intermediate" / "derived" / "highest.wav",
            result.output_files["highest"],
        ],
    ]


def test_auto_cuda_failure_retries_cpu_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run_command(args: list[object]) -> subprocess.CompletedProcess[str]:
        Path(args[-1]).write_bytes(b"filtered wav")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def backend_factory(model: str, device: str) -> FakeBackend:
        return FakeBackend(
            model,
            device,
            fail=device == "cuda",
            calls=calls,
        )

    monkeypatch.setattr(separation_service, "run_command", fake_run_command)
    result = ExportService(output_root=tmp_path).prepare_job(
        _media(tmp_path),
        device="auto",
    )
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=backend_factory,
        cuda_available=lambda: True,
    )

    with caplog.at_level("WARNING"):
        run_result = service.separate(result, mixture)

    assert run_result.actual_device == "cpu"
    assert calls == [("htdemucs", "cuda"), ("htdemucs", "cpu")]
    assert "retrying on CPU once" in caplog.text
    assert run_result.warnings


def test_failed_progress_is_reported(tmp_path: Path) -> None:
    result = _job_result(tmp_path)
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    progress: list[str] = []
    service = SeparationService(
        ffmpeg_path=tmp_path / "ffmpeg",
        backend_factory=lambda model, device: FakeBackend(model, device, fail=True),
        cuda_available=lambda: False,
    )

    with pytest.raises(RuntimeError, match="cpu backend failed"):
        service.separate(result, mixture, progress.append)

    assert progress == ["preparing", "loading_model", "separating", "failed"]


def test_demucs_backend_caches_separator_per_model_and_device(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created: list[tuple[str, str]] = []

    class FakeSeparator:
        samplerate = 44100

        def __init__(self, *, model: str, device: str) -> None:
            created.append((model, device))

        def separate_audio_file(self, path: str):
            return None, {
                "vocals": object(),
                "drums": object(),
                "bass": object(),
                "other": object(),
            }

    def fake_save_audio(source: object, path: str, *, samplerate: int) -> None:
        Path(path).write_bytes(f"{samplerate}".encode("utf-8"))

    monkeypatch.setattr(
        separation_service,
        "_load_demucs_api",
        lambda: (FakeSeparator, fake_save_audio),
    )
    clear_separator_cache()

    first = DemucsSeparatorBackend("htdemucs", "cpu")
    second = DemucsSeparatorBackend("htdemucs", "cpu")
    first.separate_to_wav(tmp_path / "mix.wav", tmp_path / "one")
    second.separate_to_wav(tmp_path / "mix.wav", tmp_path / "two")

    assert created == [("htdemucs", "cpu")]
    clear_separator_cache()


@pytest.mark.skipif(
    os.environ.get("RUN_DEMUCS_INTEGRATION") != "1",
    reason="Set RUN_DEMUCS_INTEGRATION=1 to run the real Demucs smoke test.",
)
def test_real_demucs_smoke_produces_all_outputs(tmp_path: Path) -> None:
    result = ExportService(output_root=tmp_path).prepare_job(_media(tmp_path), device="cpu")
    mixture = _write_synthetic_mix(tmp_path / "mixture.wav")
    service = SeparationService(
        ffmpeg_path=Path(os.environ.get("MUSIC_DECOMP_FFMPEG", "ffmpeg")),
    )

    run_result = service.separate(result, mixture)

    assert set(run_result.output_files) == {
        "vocals",
        "drums",
        "bass",
        "other",
        "lowest",
        "highest",
    }
    assert all(path.is_file() for path in run_result.output_files.values())
