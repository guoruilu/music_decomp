"""Command line interface for Music Decomp."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
import traceback
from typing import cast

from . import __version__
from .domain.jobs import Device, OutputFormat, SUPPORTED_DEVICES, SUPPORTED_OUTPUT_FORMATS


def _add_debug_argument(parser: argparse.ArgumentParser, *, default: object) -> None:
    parser.add_argument(
        "--debug",
        action="store_true",
        default=default,
        help="Show Python tracebacks for command failures.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="music-decomp",
        description="Offline music stem separation application.",
    )
    _add_debug_argument(parser, default=False)
    parser.add_argument(
        "--version",
        action="version",
        version=f"music-decomp {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    gui_parser = subparsers.add_parser("gui", help="Launch the desktop GUI.")
    _add_debug_argument(gui_parser, default=argparse.SUPPRESS)

    probe_parser = subparsers.add_parser("probe", help="Probe a media input.")
    probe_parser.add_argument("input", type=Path, help="Audio or video file to probe.")
    _add_debug_argument(probe_parser, default=argparse.SUPPRESS)

    separate_parser = subparsers.add_parser(
        "separate",
        help="Separate a media input into stems.",
    )
    separate_parser.add_argument("input", type=Path, help="Audio or video file to separate.")
    separate_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory root for the separation job.",
    )
    separate_parser.add_argument(
        "--device",
        choices=SUPPORTED_DEVICES,
        default="auto",
        help="Separation device to use.",
    )
    separate_parser.add_argument(
        "--format",
        choices=SUPPORTED_OUTPUT_FORMATS,
        default="wav",
        dest="output_format",
        help="Output audio format.",
    )
    _add_debug_argument(separate_parser, default=argparse.SUPPRESS)

    devices_parser = subparsers.add_parser(
        "list-recording-devices",
        help="List system-audio recording output devices.",
    )
    _add_debug_argument(devices_parser, default=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            return _run_gui()
        if args.command == "probe":
            return _run_probe(args.input)
        if args.command == "separate":
            return _run_separate(
                args.input,
                output_root=args.out,
                device=args.device,
                output_format=args.output_format,
            )
        if args.command == "list-recording-devices":
            return _run_list_recording_devices()
    except Exception as exc:
        _print_error(exc, debug=bool(getattr(args, "debug", False)))
        return 1

    parser.print_help()
    return 0


def _run_gui() -> int:
    from music_decomp import app

    return app.run_gui(argv=["music-decomp"])


def _run_probe(input_path: Path) -> int:
    pipeline = _create_file_pipeline()
    result = pipeline.probe_input(input_path)
    _write_json(
        {
            "kind": result.media_input.kind,
            "path": str(result.media_input.path),
            "title": result.media_input.title,
            "duration_seconds": result.media_input.duration_seconds,
            "sample_rate": result.media_input.sample_rate,
            "streams": list(result.stream_summary),
        }
    )
    return 0


def _run_separate(
    input_path: Path,
    *,
    output_root: Path,
    device: str,
    output_format: str,
) -> int:
    pipeline = _create_file_pipeline()
    result = pipeline.run_file(
        input_path,
        output_root=output_root,
        device=cast(Device, device),
        output_format=cast(OutputFormat, output_format),
        progress_callback=_print_progress,
    )
    _write_json(
        {
            "status": "success",
            "input_kind": result.probe.media_input.kind,
            "output_dir": str(result.output_dir),
            "metadata_path": str(result.metadata_path),
            "log_path": str(result.log_path),
            "highest_is_approximate": result.highest_is_approximate,
            "output_files": {
                stem: str(path)
                for stem, path in sorted(result.separation_result.output_files.items())
            },
        }
    )
    return 0


def _run_list_recording_devices() -> int:
    recorder = _create_recorder_service()
    devices = [
        {
            "id": device.id,
            "name": device.name,
            "channels": device.channels,
            "is_default": device.is_default,
        }
        for device in recorder.list_output_devices()
    ]
    _write_json(devices)
    return 0


def _create_file_pipeline():
    from music_decomp.services.file_pipeline import FileSeparationPipeline

    return FileSeparationPipeline()


def _create_recorder_service():
    from music_decomp.services.recorder_service import RecorderService

    return RecorderService()


def _write_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_progress(stage: str, message: str, percent: int | None) -> None:
    if percent is None:
        print(f"{stage}: {message}", file=sys.stderr)
    else:
        print(f"{stage} ({percent}%): {message}", file=sys.stderr)


def _print_error(exc: BaseException, *, debug: bool) -> None:
    if debug:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        return

    print(f"Error: {_exception_text(exc)}", file=sys.stderr)
    for label, attr in (
        ("Output", "output_dir"),
        ("Log", "log_path"),
        ("Metadata", "metadata_path"),
    ):
        value = getattr(exc, attr, None)
        if value is not None:
            print(f"{label}: {value}", file=sys.stderr)


def _exception_text(exc: BaseException) -> str:
    return str(exc) or exc.__class__.__name__
