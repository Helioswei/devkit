#!/usr/bin/env python3
"""Merge video clips with drawtext labels, intro and outro, into one mp4."""

import argparse
import subprocess
import sys
import os
import tempfile
import shutil

PREFIX = os.environ.get("DEVKIT_PREFIX", "video")

W, H = 1920, 1080


def _check_ffmpeg():
    """检查 ffmpeg/ffprobe 是否存在，不存在则报错退出。"""
    for cmd in ("ffmpeg", "ffprobe"):
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            print(f"Error: {cmd} not found.", file=sys.stderr)
            print("  Install: brew install ffmpeg", file=sys.stderr)
            sys.exit(1)


def _parse_config(config_path: str) -> dict:
    entries = []
    author = ""
    intro_dur = 0.0
    outro_dur = 0.0
    with open(config_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("author="):
                author = line.split("=", 1)[1].strip()
                continue
            if line.startswith("intro="):
                intro_dur = float(line.split("=", 1)[1].strip())
                continue
            if line.startswith("outro="):
                outro_dur = float(line.split("=", 1)[1].strip())
                continue
            parts = line.split("|")
            filename = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            start = parts[2].strip() if len(parts) > 2 else ""
            end = parts[3].strip() if len(parts) > 3 else ""
            entries.append((filename, title, start, end))
    return {"author": author, "intro": intro_dur, "outro": outro_dur, "entries": entries}


def _ffmpeg(cmd: list, label: str = "") -> subprocess.CompletedProcess:
    """Run ffmpeg/ffprobe with friendly error on failure."""
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {label or cmd[0]} failed (exit={e.returncode})", file=sys.stderr)
        if e.stderr:
            print(f"  {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: {cmd[0]} not found. Install ffmpeg first.", file=sys.stderr)
        print("  brew install ffmpeg", file=sys.stderr)
        sys.exit(1)


def _gen_intro(tmpdir: str, author: str, titles: list[str], intro_dur: float) -> None:
    intro_file = os.path.join(tmpdir, "intro.mp4")
    print(f"Generating intro ({intro_dur}s)...")

    author_fontsize = 56
    author_y = 140
    y_offset = author_y + 80
    y_spacing = 60

    vf_parts = [f"color=c=0xD0D6DC:s={W}x{H}:r=30"]
    if author:
        vf_parts.append(
            f"drawtext=text='{author}':fontsize={author_fontsize}:fontcolor=0x333333"
            f":x=(w-text_w)/2:y={author_y}"
        )
    title_y_start = y_offset
    for i, t in enumerate(titles):
        y = title_y_start + i * y_spacing
        vf_parts.append(
            f"drawtext=text='{t}':fontsize=42:fontcolor=0x333333"
            f":x=(w-text_w)/2:y={y}"
        )

    _ffmpeg([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats",
        "-f", "lavfi", "-i", ",".join(vf_parts),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-t", str(intro_dur),
        intro_file,
    ], label="intro generation")


def _process_clip(tmpdir: str, filename: str, title: str, start: str, end: str, count: int) -> str:
    outfile = os.path.join(tmpdir, f"p{count}.mp4")
    print(f"[{count}] {filename} -> {title}" + (f" ({start}-{end}s)" if start or end else ""))

    probe = _ffmpeg([
        "ffprobe", "-hide_banner", "-v", "quiet",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0", "-select_streams", "v",
        filename,
    ], label="ffprobe")
    iw, ih = map(int, probe.stdout.strip().split(","))

    scale = f"scale={W}:{H}," if (iw, ih) != (W, H) else ""

    vf = (
        f"{scale}drawtext=text='{title}':fontsize=36:fontcolor=white"
        f":x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.5:boxborderw=10"
    )

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-i", filename]
    if start:
        cmd += ["-ss", start]
    if end:
        if start:
            cmd += ["-t", str(float(end) - float(start))]
        else:
            cmd += ["-to", end]
    cmd += [
        "-vf", vf, "-r", "30",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac",
        outfile,
    ]
    _ffmpeg(cmd, label=f"clip {count}")
    return outfile


def _gen_outro(tmpdir: str, outro_dur: float) -> None:
    outro_file = os.path.join(tmpdir, "outro.mp4")
    print(f"Generating outro ({outro_dur}s)...")

    outro_vf = (
        f"color=c=0xD0D6DC:s={W}x{H}:r=30,"
        f"drawtext=text='谢谢观看':fontsize=60:fontcolor=0x333333"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
    )

    _ffmpeg([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats",
        "-f", "lavfi", "-i", outro_vf,
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-t", str(outro_dur),
        outro_file,
    ], label="outro generation")


def _merge(config: str = "config.txt") -> int:
    """Merge video clips according to config file, output output.mp4."""
    if not os.path.isfile(config):
        print(f"Config not found: {config}", file=sys.stderr)
        return 1

    cfg = _parse_config(config)
    author = cfg["author"]
    intro_dur = cfg["intro"]
    outro_dur = cfg["outro"]
    entries = cfg["entries"]

    valid_titles = [title for fname, title, _, _ in entries if os.path.isfile(fname) and title]

    tmpdir = tempfile.mkdtemp()
    try:
        list_entries = []

        if intro_dur > 0:
            _gen_intro(tmpdir, author, valid_titles, intro_dur)
            list_entries.append("file 'intro.mp4'")
        else:
            print("Intro disabled")

        count = 0
        for filename, title, start, end in entries:
            if not os.path.isfile(filename):
                print(f"SKIP: {filename} not found")
                continue
            count += 1
            _process_clip(tmpdir, filename, title, start, end, count)
            list_entries.append(f"file 'p{count}.mp4'")

        if count == 0:
            print("No clips processed")
            return 1

        if outro_dur > 0:
            _gen_outro(tmpdir, outro_dur)
            list_entries.append("file 'outro.mp4'")
        else:
            print("Outro disabled")

        list_file = os.path.join(tmpdir, "list.txt")
        with open(list_file, "w") as f:
            f.write("\n".join(list_entries) + "\n")

        print(f"Merging {count} clips + intro + outro...")
        _ffmpeg([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "output.mp4",
        ], label="final merge")

        print(f"Done: output.mp4 ({count} clips + intro + outro)")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    _check_ffmpeg()
    parser = argparse.ArgumentParser(prog=PREFIX, description="用 ffmpeg 合并视频片段，自动加片头片尾和文字水印")
    parser.add_argument("config", nargs="?", default="config.txt", help="配置文件路径（默认 config.txt）")
    args = parser.parse_args()
    return _merge(args.config)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
