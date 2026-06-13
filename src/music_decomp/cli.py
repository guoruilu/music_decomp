"""Command line interface for Music Decomp."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="music-decomp",
        description="Offline music stem separation application.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"music-decomp {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("gui", help="Launch the desktop GUI.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "gui":
        from music_decomp import app

        try:
            return app.run_gui(argv=["music-decomp"])
        except app.MissingGuiDependencyError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    parser.print_help()
    return 0
