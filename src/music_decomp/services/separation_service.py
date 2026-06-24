"""Stem separation service using lazy Demucs and FFmpeg-derived bands."""

from __future__ import annotations

import importlib
import logging
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from music_decomp.config import resolve_ffmpeg_path
from music_decomp.domain.jobs import Device, JobResult
from music_decomp.paths import is_frozen, resource_path
from music_decomp.utils.subprocesses import run_command

RAW_DEMUCS_STEMS = ("vocals", "drums", "bass", "other")
LOWEST_FILTER = "lowpass=f=250"
HIGHEST_FILTER = "highpass=f=2500,lowpass=f=12000"
INTERMEDIATE_DIR_NAME = "_intermediate"

ProgressStage = Literal[
    "preparing",
    "loading_model",
    "separating",
    "exporting",
    "done",
    "failed",
]
ProgressCallback = Callable[[ProgressStage], None]
StemSource = Literal[
    "demucs",
    "bass_copy",
    "mixture_lowpass",
    "mixture_highpass_band",
]

_SEPARATOR_CACHE: dict[tuple[str, str, str | None], Any] = {}


class SeparationError(RuntimeError):
    """Raised when a separation job cannot be completed."""


class MissingSeparationDependencyError(SeparationError):
    """Raised when optional Demucs dependencies are unavailable."""


class SeparationDeviceError(SeparationError):
    """Raised when the requested compute device cannot be used."""


class MissingModelResourceError(SeparationError):
    """Raised when packaged model resources are required but missing."""


class SeparatorBackend(Protocol):
    """Backend interface used by SeparationService and tests."""

    def separate_to_wav(
        self,
        mixture_wav: Path,
        output_dir: Path,
    ) -> Mapping[str, Path]:
        """Write raw Demucs stems as WAV files and return their paths."""


BackendFactory = Callable[[str, str, Path | None], SeparatorBackend]


@dataclass(frozen=True)
class StemOutputInfo:
    """Metadata about one exported stem file."""

    stem: str
    path: Path
    source: StemSource
    approximate: bool = False
    normalized: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class SeparationRunResult:
    """Result details returned after a separation job finishes."""

    job_result: JobResult
    mixture_wav: Path
    actual_device: str
    output_files: dict[str, Path]
    stem_info: dict[str, StemOutputInfo]
    warnings: tuple[str, ...] = ()

    @property
    def highest_is_approximate(self) -> bool:
        """Return whether the highest stem is an approximation."""
        highest = self.stem_info.get("highest")
        return bool(highest and highest.approximate)


class DemucsSeparatorBackend:
    """Thin lazy wrapper around ``demucs.api.Separator``."""

    def __init__(
        self,
        model_name: str,
        device: str,
        model_repo: str | Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.model_repo = Path(model_repo) if model_repo is not None else None

    def separate_to_wav(
        self,
        mixture_wav: Path,
        output_dir: Path,
    ) -> Mapping[str, Path]:
        """Run Demucs and save the four raw model stems as WAV files."""
        separator = _cached_demucs_separator(
            self.model_name,
            self.device,
            self.model_repo,
        )
        _, save_audio = _load_demucs_api()
        output_dir.mkdir(parents=True, exist_ok=True)

        _origin, separated = separator.separate_audio_file(str(mixture_wav))
        stem_sources = _stem_sources(separator, separated)
        sample_rate = int(getattr(separator, "samplerate", 44100))

        outputs: dict[str, Path] = {}
        for stem in RAW_DEMUCS_STEMS:
            if stem not in stem_sources:
                continue
            stem_path = output_dir / f"{stem}.wav"
            save_audio(stem_sources[stem], str(stem_path), samplerate=sample_rate)
            outputs[stem] = stem_path
        return outputs


class SeparationService:
    """Run model separation and derive lowest/highest output stems."""

    def __init__(
        self,
        *,
        ffmpeg_path: str | Path | None = None,
        backend_factory: BackendFactory | None = None,
        cuda_available: Callable[[], bool] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.ffmpeg_path = (
            Path(ffmpeg_path) if ffmpeg_path is not None else resolve_ffmpeg_path()
        )
        self._backend_factory = backend_factory or DemucsSeparatorBackend
        self._cuda_available = cuda_available
        self._logger = logger or logging.getLogger(__name__)

    def resolve_device(self, requested: Device) -> str:
        """Resolve the requested device to ``cpu`` or ``cuda``."""
        if requested == "cpu":
            return "cpu"
        if requested == "cuda":
            if not self._is_cuda_available(strict=True):
                raise SeparationDeviceError(
                    "CUDA was requested, but torch.cuda.is_available() is false."
                )
            return "cuda"
        if requested == "auto":
            return "cuda" if self._is_cuda_available(strict=False) else "cpu"
        raise SeparationDeviceError(f"Unsupported separation device: {requested!r}")

    def separate(
        self,
        result: JobResult,
        mixture_wav: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> SeparationRunResult:
        """Separate one canonical 44.1 kHz stereo mixture WAV."""
        progress = _ProgressEmitter(progress_callback)
        warnings: list[str] = []
        mixture_path = Path(mixture_wav)

        try:
            progress.emit("preparing")
            if not mixture_path.is_file():
                raise FileNotFoundError(f"Mixture WAV does not exist: {mixture_path}")

            job = result.job
            job.output_dir.mkdir(parents=True, exist_ok=True)
            intermediate_dir = job.output_dir / INTERMEDIATE_DIR_NAME
            raw_dir = intermediate_dir / "demucs"
            derived_dir = intermediate_dir / "derived"
            raw_dir.mkdir(parents=True, exist_ok=True)
            derived_dir.mkdir(parents=True, exist_ok=True)

            initial_device = self.resolve_device(job.device)
            try:
                raw_stems = self._run_backend(
                    job.model_name,
                    initial_device,
                    mixture_path,
                    raw_dir,
                    progress,
                )
                actual_device = initial_device
            except Exception as exc:
                if job.device != "auto" or initial_device != "cuda":
                    raise
                warning = (
                    "CUDA separation failed while using auto device; "
                    f"retrying on CPU once: {exc}"
                )
                self._logger.warning(warning)
                warnings.append(warning)
                raw_stems = self._run_backend(
                    job.model_name,
                    "cpu",
                    mixture_path,
                    raw_dir,
                    progress,
                )
                actual_device = "cpu"

            progress.emit("exporting")
            output_files, stem_info = self._export_outputs(
                result=result,
                mixture_wav=mixture_path,
                raw_stems=raw_stems,
                derived_dir=derived_dir,
            )
            progress.emit("done")
            return SeparationRunResult(
                job_result=result,
                mixture_wav=mixture_path,
                actual_device=actual_device,
                output_files=output_files,
                stem_info=stem_info,
                warnings=tuple(warnings),
            )
        except Exception:
            progress.emit("failed")
            raise

    def _run_backend(
        self,
        model_name: str,
        device: str,
        mixture_wav: Path,
        raw_dir: Path,
        progress: "_ProgressEmitter",
    ) -> Mapping[str, Path]:
        progress.emit("loading_model")
        backend = self._backend_factory(
            model_name,
            device,
            resolve_packaged_model_repo(),
        )
        progress.emit("separating")
        return {
            stem: Path(path)
            for stem, path in backend.separate_to_wav(mixture_wav, raw_dir).items()
        }

    def _export_outputs(
        self,
        *,
        result: JobResult,
        mixture_wav: Path,
        raw_stems: Mapping[str, Path],
        derived_dir: Path,
    ) -> tuple[dict[str, Path], dict[str, StemOutputInfo]]:
        output_files: dict[str, Path] = {}
        stem_info: dict[str, StemOutputInfo] = {}

        for stem in RAW_DEMUCS_STEMS:
            raw_path = raw_stems.get(stem)
            if raw_path is None:
                if stem in result.output_files:
                    raise SeparationError(f"Demucs did not produce required stem: {stem}")
                continue
            if stem in result.output_files:
                target_path = result.output_files[stem]
                self._copy_or_convert_audio(raw_path, target_path)
                output_files[stem] = target_path
                stem_info[stem] = StemOutputInfo(
                    stem=stem,
                    path=target_path,
                    source="demucs",
                )

        if "lowest" in result.output_files:
            target_path = result.output_files["lowest"]
            bass_path = raw_stems.get("bass")
            if bass_path is not None and Path(bass_path).is_file():
                self._copy_or_convert_audio(bass_path, target_path)
                stem_info["lowest"] = StemOutputInfo(
                    stem="lowest",
                    path=target_path,
                    source="bass_copy",
                    notes="Derived from the Demucs bass stem.",
                )
            else:
                filtered_wav = derived_dir / "lowest.wav"
                self._filter_to_wav(mixture_wav, filtered_wav, LOWEST_FILTER)
                self._copy_or_convert_audio(filtered_wav, target_path)
                stem_info["lowest"] = StemOutputInfo(
                    stem="lowest",
                    path=target_path,
                    source="mixture_lowpass",
                    approximate=True,
                    notes="Bass stem was unavailable; used mixture low-pass fallback.",
                )
            output_files["lowest"] = target_path

        if "highest" in result.output_files:
            target_path = result.output_files["highest"]
            filtered_wav = derived_dir / "highest.wav"
            self._filter_to_wav(mixture_wav, filtered_wav, HIGHEST_FILTER)
            self._copy_or_convert_audio(filtered_wav, target_path)
            output_files["highest"] = target_path
            stem_info["highest"] = StemOutputInfo(
                stem="highest",
                path=target_path,
                source="mixture_highpass_band",
                approximate=True,
                normalized=False,
                notes=(
                    "Band-pass approximation from the mixture; clipping-dependent "
                    "normalization is not applied in Step 5."
                ),
            )

        return output_files, stem_info

    def _filter_to_wav(self, source_path: Path, output_wav: Path, filter_spec: str) -> Path:
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                source_path,
                "-af",
                filter_spec,
                "-ac",
                "2",
                "-ar",
                "44100",
                "-sample_fmt",
                "s16",
                output_wav,
            ]
        )
        return output_wav

    def _copy_or_convert_audio(self, source_path: Path, target_path: Path) -> Path:
        source = Path(source_path)
        target = Path(target_path)
        if not source.is_file():
            raise SeparationError(f"Audio source does not exist: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() == target.resolve():
            return target
        if target.suffix.lower() == ".wav":
            shutil.copy2(source, target)
        else:
            run_command([self.ffmpeg_path, "-y", "-i", source, target])
        return target

    def _is_cuda_available(self, *, strict: bool) -> bool:
        if self._cuda_available is not None:
            return bool(self._cuda_available())
        try:
            torch = importlib.import_module("torch")
        except ImportError as exc:
            if strict:
                raise SeparationDeviceError(
                    "CUDA was requested, but PyTorch is not installed."
                ) from exc
            return False

        cuda = getattr(torch, "cuda", None)
        try:
            available = bool(cuda is not None and cuda.is_available())
        except Exception as exc:
            if strict:
                raise SeparationDeviceError(
                    "CUDA was requested, but torch.cuda.is_available() failed."
                ) from exc
            return False
        return available


class _ProgressEmitter:
    def __init__(self, callback: ProgressCallback | None) -> None:
        self._callback = callback

    def emit(self, stage: ProgressStage) -> None:
        if self._callback is not None:
            self._callback(stage)


def clear_separator_cache() -> None:
    """Clear the process-local Demucs separator cache."""
    _SEPARATOR_CACHE.clear()


def resolve_packaged_model_repo() -> Path | None:
    """Return the bundled model repository path, or None in source fallback mode."""
    models_dir = resource_path("models")
    manifest_path = models_dir / "manifest.json"
    if manifest_path.is_file():
        return models_dir
    if is_frozen():
        raise MissingModelResourceError(
            "Packaged model manifest is missing. Expected bundled model assets at "
            f"{manifest_path}."
        )
    return None


def _cached_demucs_separator(
    model_name: str,
    device: str,
    model_repo: str | Path | None = None,
) -> Any:
    repo_path = Path(model_repo) if model_repo is not None else None
    repo_key = str(repo_path.resolve()) if repo_path is not None else None
    key = (model_name, device, repo_key)
    if key not in _SEPARATOR_CACHE:
        separator_class, _save_audio = _load_demucs_api()
        kwargs: dict[str, object] = {"model": model_name, "device": device}
        if repo_path is not None:
            kwargs["repo"] = str(repo_path)
        _SEPARATOR_CACHE[key] = separator_class(**kwargs)
    return _SEPARATOR_CACHE[key]


def _load_demucs_api() -> tuple[type[Any], Callable[..., Any]]:
    try:
        demucs_api = importlib.import_module("demucs.api")
    except ImportError as exc:
        raise MissingSeparationDependencyError(
            "Demucs is not installed. Install the optional 'separation' extra "
            "to enable model-based separation."
        ) from exc

    try:
        separator_class = demucs_api.Separator
        save_audio = demucs_api.save_audio
    except AttributeError as exc:
        raise MissingSeparationDependencyError(
            "Installed demucs.api does not provide Separator/save_audio."
        ) from exc
    return cast(type[Any], separator_class), cast(Callable[..., Any], save_audio)


def _stem_sources(separator: Any, separated: Any) -> Mapping[str, Any]:
    if isinstance(separated, Mapping):
        return {str(name): source for name, source in separated.items()}

    source_names = getattr(separator, "sources", None)
    if source_names is None:
        model = getattr(separator, "model", None)
        source_names = getattr(model, "sources", None)
    if source_names is None:
        raise SeparationError(
            "Demucs returned an unsupported separation result; expected a mapping "
            "or a result with separator source names."
        )

    try:
        return {
            str(stem): separated[index]
            for index, stem in enumerate(source_names)
        }
    except Exception as exc:
        raise SeparationError("Unable to map Demucs sources to stem names.") from exc
