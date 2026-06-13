"""Subprocess helpers with consistent command error messages."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

CommandArg = str | Path
STDERR_TAIL_CHARS = 4000


class CommandExecutionError(RuntimeError):
    """Raised when a subprocess exits unsuccessfully."""

    def __init__(
        self,
        args: Sequence[str],
        *,
        exit_code: int,
        stderr: str,
    ) -> None:
        self.args_list = list(args)
        self.exit_code = exit_code
        self.stderr = stderr
        executable = self.args_list[0] if self.args_list else "<empty command>"
        stderr_tail = _tail(stderr)
        super().__init__(
            "Command failed "
            f"(executable: {executable}, exit code: {exit_code}, stderr tail: {stderr_tail})"
        )


def run_command(args: Sequence[CommandArg]) -> subprocess.CompletedProcess[str]:
    """Run a command with list arguments and raise detailed errors on failure."""
    command = _normalize_args(args)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CommandExecutionError(
            command,
            exit_code=-1,
            stderr=str(exc),
        ) from exc
    if result.returncode != 0:
        raise CommandExecutionError(
            command,
            exit_code=result.returncode,
            stderr=result.stderr or "",
        )
    return result


def _normalize_args(args: Sequence[CommandArg]) -> list[str]:
    if isinstance(args, (str, bytes)):
        raise TypeError("Subprocess arguments must be a sequence, not a shell string")
    command = [str(arg) for arg in args]
    if not command:
        raise ValueError("Subprocess command must not be empty")
    return command


def _tail(value: str) -> str:
    if not value:
        return ""
    return value[-STDERR_TAIL_CHARS:]
