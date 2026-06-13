from __future__ import annotations

"""Subprocess execution helpers.

Two distinct patterns extracted from across devkit modules:
- run(): print command + stream output + return exit code (non-blocking)
- run_check(): capture output + fail-fast with error message (blocking)
"""

import subprocess
import sys


def run(cmd: list[str], desc: str | None = None, timeout: int | None = None) -> int:
    """Run command with live streaming output. Returns exit code.

    Prints the command before execution. Caller decides what to do with
    the return code.  timeout: seconds, None means no limit.
    """
    if desc:
        print(f"  {desc}")
    print(f"$ {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"Error: command timed out ({timeout}s)", file=sys.stderr)
        print(f"  Command: {' '.join(cmd)}", file=sys.stderr)
        return -1


def run_check(
    cmd: list[str], label: str | None = None
) -> subprocess.CompletedProcess:
    """Run command, capture output. Exit on failure with error message.

    Returns CompletedProcess on success. On failure, prints the command
    and stderr, then exits with code 1.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if label:
            print(f"Error: {label} failed.", file=sys.stderr)
        print(f"  Command: {' '.join(cmd)}", file=sys.stderr)
        print(f"  Output: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result
