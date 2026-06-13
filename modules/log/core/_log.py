#!/usr/bin/env python3
"""Log parsing: grep log files with predefined subsystem patterns."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
from core._patterns import DELETE, PARSE

PREFIX = os.environ.get("DEVKIT_PREFIX", "log")


def _pattern_str(patterns) -> str:
    return "|".join(patterns)


def list_subsystems() -> None:
    """Print available subsystems and their pattern counts."""
    print("保留匹配行 (parse):")
    for name, patterns in PARSE.items():
        print(f"  {name:12s}  {len(patterns)} patterns")
    print("\n删除匹配行 (delete):")
    for name, patterns in DELETE.items():
        print(f"  {name:12s}  {len(patterns)} patterns")


def parse(subsystem: str, logfiles: list[str]) -> int:
    """Keep lines matching subsystem patterns."""
    patterns = PARSE.get(subsystem)
    if not patterns:
        print(f"Error: unknown subsystem '{subsystem}'. Run '{PREFIX} --list' for available subsystems.", file=sys.stderr)
        return 1
    rc = 0
    for logfile in logfiles:
        path = Path(logfile)
        if not path.is_file():
            print(f"Error: file not found: {logfile}", file=sys.stderr)
            rc = 1
            continue
        cmd = ["grep", "--color=always", "-rn", "-E", _pattern_str(patterns), logfile]
        ret = subprocess.run(cmd).returncode
        if ret != 0:
            rc = ret
    return rc


def delete(subsystem: str, logfiles: list[str]) -> int:
    """Remove lines matching subsystem patterns."""
    patterns = DELETE.get(subsystem)
    if not patterns:
        print(f"Error: unknown subsystem '{subsystem}'. Run '{PREFIX} --list' for available subsystems.", file=sys.stderr)
        return 1
    rc = 0
    for logfile in logfiles:
        path = Path(logfile)
        if not path.is_file():
            print(f"Error: file not found: {logfile}", file=sys.stderr)
            rc = 1
            continue
        cmd = ["grep", "--color=always", "-rn", "-v", "-E", _pattern_str(patterns), logfile]
        ret = subprocess.run(cmd).returncode
        if ret != 0:
            rc = ret
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(prog=PREFIX, description="按子系统关键词过滤日志文件")
    parser.add_argument("subsystem", nargs="?", help="子系统名称 (activity, crash, wms, ime, input 等，--list 查看全部)")
    parser.add_argument("files", nargs="*", help="日志文件路径")
    parser.add_argument("-d", "--delete", action="store_true", help="删除匹配行（默认保留匹配行）")
    parser.add_argument("--list", action="store_true", help="列出所有支持的子系统")
    args = parser.parse_args()

    if args.list or not args.subsystem:
        list_subsystems()
        return 0
    if not args.files:
        print("Error: at least one log file required", file=sys.stderr)
        return 1
    if args.delete:
        return delete(args.subsystem, args.files)
    return parse(args.subsystem, args.files)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
