#!/usr/bin/env python3
"""Line filtering: keep, remove, or extract line ranges from files."""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional


PREFIX = os.environ.get("DEVKIT_PREFIX", "log")


def _check_file(path: str) -> Optional[Path]:
    p = Path(path)
    if not p.is_file():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return None
    return p


def include(path: str, pattern: str) -> int:
    """Keep lines matching a single pattern -> *.filter"""
    p = _check_file(path)
    if p is None:
        return 1
    out = p.with_suffix(p.suffix + ".filter")
    count = 0
    with open(p, encoding="utf-8", errors="replace") as fin, open(out, "w", encoding="utf-8") as fout:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            print(f"Error: invalid regex: {e}", file=sys.stderr)
            return 1
        for line in fin:
            if rx.search(line):
                fout.write(line)
                count += 1
    print(f"-> {out} ({count} lines)")
    return 0


def include_any(path, patterns) -> int:
    """Keep lines matching any of the patterns -> *.filter"""
    p = _check_file(path)
    if p is None:
        return 1
    compiled = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as e:
            print(f"Error: invalid regex '{pat}': {e}", file=sys.stderr)
            return 1
    out = p.with_suffix(p.suffix + ".filter")
    count = 0
    with open(p, encoding="utf-8", errors="replace") as fin, open(out, "w", encoding="utf-8") as fout:
        for line in fin:
            if any(rx.search(line) for rx in compiled):
                fout.write(line)
                count += 1
    print(f"-> {out} ({count} lines)")
    return 0


def exclude(path: str, pattern: str) -> int:
    """Remove lines matching a single pattern -> *.del"""
    p = _check_file(path)
    if p is None:
        return 1
    out_base = p.with_suffix(p.suffix + ".del")
    if out_base.exists():
        out_base = Path(str(out_base) + ".del")
    try:
        rx = re.compile(pattern)
    except re.error as e:
        print(f"Error: invalid regex: {e}")
        return 1
    count = 0
    with open(p, encoding="utf-8", errors="replace") as fin, open(out_base, "w", encoding="utf-8") as fout:
        for line in fin:
            if not rx.search(line):
                fout.write(line)
                count += 1
    print(f"-> {out_base} ({count} lines)")
    return 0


def exclude_any(path, patterns) -> int:
    """Remove lines matching any of the patterns -> *.del"""
    p = _check_file(path)
    if p is None:
        return 1
    compiled = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as e:
            print(f"Error: invalid regex '{pat}': {e}", file=sys.stderr)
            return 1
    out_base = p.with_suffix(p.suffix + ".del")
    if out_base.exists():
        out_base = Path(str(out_base) + ".del")
    count = 0
    with open(p, encoding="utf-8", errors="replace") as fin, open(out_base, "w", encoding="utf-8") as fout:
        for line in fin:
            if not any(rx.search(line) for rx in compiled):
                fout.write(line)
                count += 1
    print(f"-> {out_base} ({count} lines)")
    return 0


def line_range(path: str, start: int, end: int) -> int:
    """Extract lines [start, end] (1-based) -> *.line"""
    p = _check_file(path)
    if p is None:
        return 1
    if start < 1 or end < start:
        print(f"Error: invalid range [{start}, {end}]", file=sys.stderr)
        return 1
    out = p.with_suffix(p.suffix + ".line")
    count = 0
    with open(p, encoding="utf-8", errors="replace") as fin, open(out, "w", encoding="utf-8") as fout:
        for i, line in enumerate(fin, 1):
            if i > end:
                break
            if i >= start:
                fout.write(line)
                count += 1
    print(f"-> {out} ({count} lines)")
    return 0


ACTION_MAP = {
    "keep": include,
    "keep-any": include_any,
    "remove": exclude,
    "remove-any": exclude_any,
    "range": line_range,
}


def main() -> int:
    parser = argparse.ArgumentParser(prog=f"{PREFIX} filter", description="按正则表达式保留或删除日志中的行")
    parser.add_argument("action", choices=list(ACTION_MAP.keys()), help="操作: keep, keep-any, remove, remove-any, range")
    parser.add_argument("file", help="输入文件")
    parser.add_argument("patterns", nargs="*", help="正则表达式或行号范围")
    args = parser.parse_args()

    fn = ACTION_MAP[args.action]

    if args.action in ("keep", "remove"):
        if not args.patterns:
            print(f"Error: {args.action} requires a pattern", file=sys.stderr)
            return 1
        return fn(args.file, args.patterns[0])

    if args.action in ("keep-any", "remove-any"):
        if not args.patterns:
            print(f"Error: {args.action} requires at least one pattern", file=sys.stderr)
            return 1
        return fn(args.file, args.patterns)

    if args.action == "range":
        if len(args.patterns) != 2:
            print("Error: range requires start and end line numbers", file=sys.stderr)
            return 1
        return line_range(args.file, int(args.patterns[0]), int(args.patterns[1]))

    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
