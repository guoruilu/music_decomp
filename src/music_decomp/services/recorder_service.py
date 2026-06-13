"""System-audio recorder service with lazy SoundCard loopback support."""

from __future__ import annotations

import array
import importlib
import math
import sys
import threading
import wave
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from music_decomp.domain.media import MediaInput
from music_decomp.paths import project_root

DEFAULT_SAMPLE_RATE = 48_000
DEFAULT_CHANNELS = 2
DEFAULT_CHUNK_FRAMES = 4_096
DEFAULT_STOP_TIMEOUT_SECONDS = 5.0

LOOPBACK_UNAVAILABLE_MESSAGE = (
    "System audio recording is unavailable for this output device. "
    "Try another output device or use a local file."
)

Clock = Callable[[], datetime]


class RecorderError(RuntimeError):
    """Raised when system-audio recording cannot complete."""


class MissingRecorderDependencyError(RecorderError):
    """Raised when optional recording dependencies are unavailable."""


class RecorderUnavailableError(RecorderError):
    """Raised when WASAPI loopback cannot be opened for the selected device."""


class RecorderStateError(RecorderError):
    """Raised when recorder lifecycle methods are called in an invalid state."""


@dataclass(frozen=True)
class RecordingDevice:
    """Output device that may be recordable through WASAPI loopback."""

    id: str
    name: str
    channels: int | None = None
    is_default: bool = False


class WavWriter(Protocol):
    """WAV writer interface used by RecorderService and tests."""

    def write_frames(self, frames: object) -> None:
        """Write one chunk of frames."""

    def close(self) -> None:
        """Finalize and close the WAV file."""


class LoopbackRecordingSource(Protocol):
    """Source of loopback recording chunks."""

    def chunks(self, stop_event: threading.Event) -> Iterable[object]:
        """Yield audio chunks until ``stop_event`` is set."""


class RecorderBackend(Protocol):
    """Backend interface for device enumeration and loopback capture."""

    def list_output_devices(self) -> list[RecordingDevice]:
        """Return available output devices."""

    def default_output_device(self) -> RecordingDevice | None:
        """Return the system default output device, if one is available."""

    def open_loopback_recorder(
        self,
        device_id: str,
        sample_rate: int,
        channels: int,
        chunk_frames: int,
    ) -> LoopbackRecordingSource:
        """Prepare a stop-aware loopback source for a device."""


WavWriterFactory = Callable[[Path, int, int], WavWriter]


def default_recordings_root() -> Path:
    """Return the default source-mode recordings root."""
    return project_root() / "recordings"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class RecorderService:
    """Record Windows system audio on a background worker thread."""

    def __init__(
        self,
        *,
        backend: RecorderBackend | None = None,
        writer_factory: WavWriterFactory | None = None,
        recordings_root: str | Path | None = None,
        clock: Clock | None = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_frames: int = DEFAULT_CHUNK_FRAMES,
        stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if channels <= 0:
            raise ValueError("channels must be positive")
        if chunk_frames <= 0:
            raise ValueError("chunk_frames must be positive")

        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.chunk_frames = int(chunk_frames)
        self.recordings_root = (
            Path(recordings_root)
            if recordings_root is not None
            else default_recordings_root()
        )
        self.stop_timeout_seconds = float(stop_timeout_seconds)

        self._backend = backend or SoundCardLoopbackBackend()
        self._writer_factory = writer_factory or StdlibWaveWriter
        self._clock = clock or _default_clock
        self._lock = threading.Lock()

        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._output_path: Path | None = None
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None
        self._is_recording = False
        self._peak_level = 0.0
        self._worker_error: RecorderError | None = None

    def list_output_devices(self) -> list[RecordingDevice]:
        """Return available output devices for future loopback recording."""
        return self._backend.list_output_devices()

    def default_output_device(self) -> RecordingDevice:
        """Return the system default output device."""
        device = self._backend.default_output_device()
        if device is None:
            raise RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE)
        return device

    def start_recording(
        self,
        device_id: str | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        """Start recording on a worker thread and return the target WAV path."""
        with self._lock:
            if self._thread is not None:
                raise RecorderStateError("A recording is already active.")

        selected_device_id = device_id or self.default_output_device().id
        target_path = self._resolve_output_path(output_path)
        source = self._backend.open_loopback_recorder(
            selected_device_id,
            self.sample_rate,
            self.channels,
            self.chunk_frames,
        )
        writer = self._writer_factory(target_path, self.sample_rate, self.channels)
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._record_worker,
            args=(source, writer, stop_event),
            name="RecorderServiceWorker",
            daemon=True,
        )

        with self._lock:
            self._thread = thread
            self._stop_event = stop_event
            self._output_path = target_path
            self._start_time = self._clock()
            self._end_time = None
            self._is_recording = True
            self._peak_level = 0.0
            self._worker_error = None

        try:
            thread.start()
        except Exception:
            with self._lock:
                self._reset_locked()
            writer.close()
            raise

        return target_path

    def stop_recording(self) -> MediaInput:
        """Stop the worker, finalize the WAV, and return a recording input."""
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
            output_path = self._output_path
            start_time = self._start_time
            if (
                thread is None
                or stop_event is None
                or output_path is None
                or start_time is None
            ):
                raise RecorderStateError("No recording is active.")

        stop_event.set()
        thread.join(timeout=self.stop_timeout_seconds)
        if thread.is_alive():
            raise RecorderError("Recording worker did not stop within the timeout.")

        with self._lock:
            worker_error = self._worker_error
            end_time = self._end_time or self._clock()
            duration_seconds = max(0.0, (end_time - start_time).total_seconds())
            sample_rate = self.sample_rate
            self._reset_locked()

        if worker_error is not None:
            raise worker_error

        return MediaInput(
            kind="recording",
            path=output_path,
            title=output_path.stem,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
        )

    @property
    def is_recording(self) -> bool:
        """Return whether a recording worker is currently active."""
        with self._lock:
            return self._is_recording

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed recording time for UI status display."""
        with self._lock:
            start_time = self._start_time
            if start_time is None:
                return 0.0
            end_time = self._clock() if self._is_recording else self._end_time
            if end_time is None:
                return 0.0
            return max(0.0, (end_time - start_time).total_seconds())

    @property
    def peak_level(self) -> float:
        """Return the latest chunk peak level, clipped to the 0.0-1.0 range."""
        with self._lock:
            return self._peak_level

    def _resolve_output_path(self, output_path: str | Path | None) -> Path:
        if output_path is not None:
            return Path(output_path)
        timestamp = self._clock().strftime("%Y%m%d-%H%M%S")
        return self.recordings_root / f"{timestamp}-recording.wav"

    def _record_worker(
        self,
        source: LoopbackRecordingSource,
        writer: WavWriter,
        stop_event: threading.Event,
    ) -> None:
        worker_error: RecorderError | None = None
        try:
            for chunk in source.chunks(stop_event):
                if _is_empty_frames(chunk):
                    continue
                peak_level = _chunk_peak_level(chunk)
                writer.write_frames(chunk)
                with self._lock:
                    self._peak_level = peak_level
        except RecorderError as exc:
            worker_error = exc
        except Exception as exc:  # pragma: no cover - defensive wrapper
            worker_error = RecorderError(f"Recording failed: {exc}")

        try:
            writer.close()
        except Exception as exc:  # pragma: no cover - defensive wrapper
            if worker_error is None:
                worker_error = RecorderError(f"Failed to finalize recording WAV: {exc}")

        with self._lock:
            self._end_time = self._clock()
            self._is_recording = False
            self._worker_error = worker_error

    def _reset_locked(self) -> None:
        self._thread = None
        self._stop_event = None
        self._output_path = None
        self._start_time = None
        self._end_time = None
        self._is_recording = False
        self._peak_level = 0.0
        self._worker_error = None


class SoundCardLoopbackBackend:
    """SoundCard-backed Windows WASAPI loopback implementation."""

    def __init__(self, soundcard_module: object | None = None) -> None:
        self._soundcard_module = soundcard_module

    def list_output_devices(self) -> list[RecordingDevice]:
        """Return SoundCard speakers as loopback-capable output devices."""
        soundcard = self._load_soundcard()
        default_id = None
        try:
            default_speaker = soundcard.default_speaker()
            default_id = str(getattr(default_speaker, "id", ""))
        except Exception:
            default_id = None
        return [
            _recording_device_from_soundcard(device, default_id=default_id)
            for device in soundcard.all_speakers()
        ]

    def default_output_device(self) -> RecordingDevice | None:
        """Return SoundCard's default speaker."""
        soundcard = self._load_soundcard()
        try:
            default_speaker = soundcard.default_speaker()
        except Exception as exc:
            raise RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE) from exc
        return _recording_device_from_soundcard(
            default_speaker,
            default_id=str(getattr(default_speaker, "id", "")),
        )

    def open_loopback_recorder(
        self,
        device_id: str,
        sample_rate: int,
        channels: int,
        chunk_frames: int,
    ) -> LoopbackRecordingSource:
        """Open a SoundCard loopback microphone for the selected speaker."""
        soundcard = self._load_soundcard()
        try:
            microphone = soundcard.get_microphone(device_id, include_loopback=True)
        except Exception as exc:
            raise RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE) from exc
        return _SoundCardLoopbackSource(
            microphone=microphone,
            sample_rate=sample_rate,
            channels=channels,
            chunk_frames=chunk_frames,
        )

    def _load_soundcard(self) -> Any:
        if self._soundcard_module is not None:
            return self._soundcard_module
        try:
            self._soundcard_module = importlib.import_module("soundcard")
        except ImportError as exc:
            raise MissingRecorderDependencyError(
                "SoundCard is not installed. Install the optional 'recorder' extra "
                "to enable system audio recording."
            ) from exc
        return self._soundcard_module


@dataclass
class _SoundCardLoopbackSource:
    microphone: object
    sample_rate: int
    channels: int
    chunk_frames: int

    def chunks(self, stop_event: threading.Event) -> Iterator[object]:
        try:
            with self.microphone.recorder(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_frames,
            ) as recorder:
                while not stop_event.is_set():
                    yield recorder.record(numframes=self.chunk_frames)
        except Exception as exc:
            raise RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE) from exc


class StdlibWaveWriter:
    """Small float-to-PCM WAV writer that avoids optional soundfile imports."""

    def __init__(self, path: Path, sample_rate: int, channels: int) -> None:
        if channels != DEFAULT_CHANNELS:
            raise ValueError("StdlibWaveWriter currently writes stereo WAV files only")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._wave = wave.open(str(self.path), "wb")
        self._wave.setnchannels(channels)
        self._wave.setsampwidth(2)
        self._wave.setframerate(sample_rate)

    def write_frames(self, frames: object) -> None:
        samples = array.array("h")
        for left, right in _iter_stereo_pairs(frames):
            samples.append(_float_to_pcm16(left))
            samples.append(_float_to_pcm16(right))
        if not samples:
            return
        if sys.byteorder != "little":
            samples.byteswap()
        self._wave.writeframes(samples.tobytes())

    def close(self) -> None:
        wave_file = self._wave
        if wave_file is not None:
            self._wave = None
            wave_file.close()


def _recording_device_from_soundcard(
    device: object,
    *,
    default_id: str | None,
) -> RecordingDevice:
    device_id = str(getattr(device, "id", "") or getattr(device, "name", "") or device)
    name = str(getattr(device, "name", "") or device_id)
    channels = _optional_int(getattr(device, "channels", None))
    return RecordingDevice(
        id=device_id,
        name=name,
        channels=channels,
        is_default=bool(default_id and device_id == default_id),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_empty_frames(frames: object) -> bool:
    if frames is None:
        return True
    shape = getattr(frames, "shape", None)
    if shape is not None and len(shape) > 0:
        return int(shape[0]) == 0
    try:
        return len(frames) == 0  # type: ignore[arg-type]
    except TypeError:
        return False


def _chunk_peak_level(frames: object) -> float:
    peak = 0.0
    for left, right in _iter_stereo_pairs(frames):
        peak = max(peak, abs(left), abs(right))
    return max(0.0, min(1.0, peak))


def _iter_stereo_pairs(frames: object) -> Iterator[tuple[float, float]]:
    try:
        iterator = iter(frames)  # type: ignore[arg-type]
    except TypeError:
        return

    pending_left: float | None = None
    for item in iterator:
        pair = _row_to_stereo_pair(item)
        if pair is not None:
            yield pair
            continue

        sample = _safe_float(item)
        if pending_left is None:
            pending_left = sample
        else:
            yield pending_left, sample
            pending_left = None

    if pending_left is not None:
        yield pending_left, pending_left


def _row_to_stereo_pair(row: object) -> tuple[float, float] | None:
    if isinstance(row, (str, bytes, bytearray)):
        return None
    try:
        row_length = len(row)  # type: ignore[arg-type]
    except TypeError:
        return None
    if row_length == 0:
        return 0.0, 0.0
    try:
        left = _safe_float(row[0])  # type: ignore[index]
        right = _safe_float(row[1] if row_length > 1 else row[0])  # type: ignore[index]
    except (TypeError, IndexError):
        return None
    return left, right


def _safe_float(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return number


def _float_to_pcm16(value: float) -> int:
    value = _safe_float(value)
    if value <= -1.0:
        return -32_768
    if value >= 1.0:
        return 32_767
    return int(round(value * 32_767))
