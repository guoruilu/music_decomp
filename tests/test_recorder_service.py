from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from music_decomp.domain.media import MediaInput
from music_decomp.services.recorder_service import (
    LOOPBACK_UNAVAILABLE_MESSAGE,
    RecorderService,
    RecorderStateError,
    RecorderUnavailableError,
    RecordingDevice,
    SoundCardLoopbackBackend,
    StdlibWaveWriter,
)


class ManualClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class FakeChunkSource:
    def __init__(self, chunks: list[object] | None = None) -> None:
        self._chunks = list(chunks or [])
        self.started = threading.Event()
        self.thread_name: str | None = None

    def chunks(self, stop_event: threading.Event) -> Any:
        self.thread_name = threading.current_thread().name
        self.started.set()
        for chunk in self._chunks:
            yield chunk
        while not stop_event.is_set():
            stop_event.wait(0.01)


class FailingChunkSource:
    def chunks(self, stop_event: threading.Event) -> Any:
        raise RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE)
        yield None


class FakeBackend:
    def __init__(
        self,
        *,
        devices: list[RecordingDevice] | None = None,
        default_device: RecordingDevice | None = None,
        source: Any | None = None,
        open_error: Exception | None = None,
    ) -> None:
        self.devices = devices or [
            RecordingDevice(id="speaker-1", name="Speakers", channels=2, is_default=True)
        ]
        self.default_device = default_device or self.devices[0]
        self.source = source or FakeChunkSource()
        self.open_error = open_error
        self.open_calls: list[tuple[str, int, int, int]] = []

    def list_output_devices(self) -> list[RecordingDevice]:
        return list(self.devices)

    def default_output_device(self) -> RecordingDevice | None:
        return self.default_device

    def open_loopback_recorder(
        self,
        device_id: str,
        sample_rate: int,
        channels: int,
        chunk_frames: int,
    ) -> Any:
        self.open_calls.append((device_id, sample_rate, channels, chunk_frames))
        if self.open_error is not None:
            raise self.open_error
        return self.source


class FakeWriter:
    def __init__(
        self,
        path: Path,
        sample_rate: int,
        channels: int,
        write_event: threading.Event,
    ) -> None:
        self.path = Path(path)
        self.sample_rate = sample_rate
        self.channels = channels
        self.frames: list[object] = []
        self.closed = False
        self._write_event = write_event

    def write_frames(self, frames: object) -> None:
        self.frames.append(frames)
        self._write_event.set()

    def close(self) -> None:
        self.closed = True


class FakeWriterFactory:
    def __init__(self) -> None:
        self.write_event = threading.Event()
        self.writers: list[FakeWriter] = []

    def __call__(self, path: Path, sample_rate: int, channels: int) -> FakeWriter:
        writer = FakeWriter(path, sample_rate, channels, self.write_event)
        self.writers.append(writer)
        return writer


@dataclass
class FakeSpeaker:
    id: str
    name: str
    channels: int


class FakeSoundCardModule:
    def __init__(self) -> None:
        self.speakers = [
            FakeSpeaker(id="speaker-a", name="Headphones", channels=2),
            FakeSpeaker(id="speaker-b", name="HDMI Output", channels=8),
        ]

    def all_speakers(self) -> list[FakeSpeaker]:
        return list(self.speakers)

    def default_speaker(self) -> FakeSpeaker:
        return self.speakers[1]


def _fixed_time() -> datetime:
    return datetime(2026, 6, 13, 9, 8, 7, tzinfo=timezone.utc)


def test_soundcard_backend_maps_mocked_speaker_enumeration() -> None:
    backend = SoundCardLoopbackBackend(soundcard_module=FakeSoundCardModule())

    devices = backend.list_output_devices()

    assert devices == [
        RecordingDevice(
            id="speaker-a",
            name="Headphones",
            channels=2,
            is_default=False,
        ),
        RecordingDevice(
            id="speaker-b",
            name="HDMI Output",
            channels=8,
            is_default=True,
        ),
    ]
    assert backend.default_output_device() == devices[1]


def test_service_lists_and_returns_default_output_device() -> None:
    devices = [
        RecordingDevice(id="speaker-1", name="Speakers", channels=2),
        RecordingDevice(id="speaker-2", name="Headphones", channels=2, is_default=True),
    ]
    backend = FakeBackend(devices=devices, default_device=devices[1])
    service = RecorderService(backend=backend)

    assert service.list_output_devices() == devices
    assert service.default_output_device() == devices[1]


def test_recording_chunks_are_written_as_stereo_and_stop_returns_media_input(
    tmp_path: Path,
) -> None:
    clock = ManualClock(_fixed_time())
    chunks = [[(0.50, -0.25), (0.10, 0.75)]]
    source = FakeChunkSource(chunks=chunks)
    backend = FakeBackend(source=source)
    writer_factory = FakeWriterFactory()
    service = RecorderService(
        backend=backend,
        writer_factory=writer_factory,
        recordings_root=tmp_path / "recordings",
        clock=clock,
    )
    output_path = tmp_path / "take.wav"

    assert service.start_recording("speaker-1", output_path) == output_path
    assert source.started.wait(timeout=1.0)
    assert writer_factory.write_event.wait(timeout=1.0)

    clock.advance(2.5)
    assert service.is_recording
    assert service.elapsed_seconds == pytest.approx(2.5)
    assert service.peak_level == pytest.approx(0.75)

    media_input = service.stop_recording()

    assert isinstance(media_input, MediaInput)
    assert media_input.kind == "recording"
    assert media_input.path == output_path
    assert media_input.title == "take"
    assert media_input.duration_seconds == pytest.approx(2.5)
    assert media_input.sample_rate == 48_000
    assert backend.open_calls == [("speaker-1", 48_000, 2, 4_096)]
    assert writer_factory.writers[0].frames == chunks
    assert writer_factory.writers[0].closed


def test_stop_recording_when_inactive_raises_clear_state_error(tmp_path: Path) -> None:
    service = RecorderService(
        backend=FakeBackend(),
        writer_factory=FakeWriterFactory(),
        recordings_root=tmp_path / "recordings",
    )

    with pytest.raises(RecorderStateError, match="No recording is active."):
        service.stop_recording()


def test_default_recording_path_uses_injected_root_and_clock(tmp_path: Path) -> None:
    service = RecorderService(
        backend=FakeBackend(),
        writer_factory=FakeWriterFactory(),
        recordings_root=tmp_path / "recordings",
        clock=_fixed_time,
    )

    output_path = service.start_recording("speaker-1")

    assert output_path == tmp_path / "recordings" / "20260613-090807-recording.wav"
    service.stop_recording()


def test_loopback_unavailable_raises_required_message(tmp_path: Path) -> None:
    service = RecorderService(
        backend=FakeBackend(
            open_error=RecorderUnavailableError(LOOPBACK_UNAVAILABLE_MESSAGE)
        ),
        writer_factory=FakeWriterFactory(),
        recordings_root=tmp_path / "recordings",
    )

    with pytest.raises(RecorderUnavailableError) as exc_info:
        service.start_recording("missing-speaker", tmp_path / "missing.wav")

    assert str(exc_info.value) == LOOPBACK_UNAVAILABLE_MESSAGE
    assert not service.is_recording


def test_worker_loopback_failure_raises_required_message_on_stop(
    tmp_path: Path,
) -> None:
    service = RecorderService(
        backend=FakeBackend(source=FailingChunkSource()),
        writer_factory=FakeWriterFactory(),
        recordings_root=tmp_path / "recordings",
    )

    service.start_recording("speaker-1", tmp_path / "failed.wav")

    with pytest.raises(RecorderUnavailableError) as exc_info:
        service.stop_recording()

    assert str(exc_info.value) == LOOPBACK_UNAVAILABLE_MESSAGE


def test_start_recording_runs_on_background_thread_until_stop(tmp_path: Path) -> None:
    source = FakeChunkSource()
    service = RecorderService(
        backend=FakeBackend(source=source),
        writer_factory=FakeWriterFactory(),
        recordings_root=tmp_path / "recordings",
    )

    service.start_recording("speaker-1", tmp_path / "async.wav")

    assert source.started.wait(timeout=1.0)
    assert source.thread_name == "RecorderServiceWorker"
    assert service.is_recording

    media_input = service.stop_recording()

    assert media_input.path == tmp_path / "async.wav"
    assert not service.is_recording


def test_stdlib_wave_writer_writes_stereo_pcm_wav(tmp_path: Path) -> None:
    output_path = tmp_path / "writer.wav"
    writer = StdlibWaveWriter(output_path, sample_rate=48_000, channels=2)

    writer.write_frames([(1.0, -1.0), (0.0, 0.5)])
    writer.close()

    with wave.open(str(output_path), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getframerate() == 48_000
        assert wav.getsampwidth() == 2
        assert wav.getnframes() == 2
