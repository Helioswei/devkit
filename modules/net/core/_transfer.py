#!/usr/bin/env python3
"""SCP file transfer to/from remote server."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

from _ssh import scp_upload_cmd, scp_download_cmd
from _run import run
from core._base import load_config, add_env_arg

PREFIX = os.environ.get("DEVKIT_PREFIX", "net")


def upload(cfg: dict, local: str, remote: str | None = None) -> int:
    """Upload local file/folder to server."""
    local = os.path.abspath(local)
    if not os.path.exists(local):
        print(f"Error: {local} does not exist", file=sys.stderr)
        return 1
    recursive = os.path.isdir(local)
    remote_path = remote if remote else f"~/{os.path.basename(local)}"
    cmd = scp_upload_cmd(local, cfg["SSH_HOST"], remote_path, port=cfg["SSH_PORT"], recursive=recursive)
    return run(cmd)


def download(cfg: dict, remote_path: str, local: str | None = None) -> int:
    """Download remote file/folder to local directory."""
    if not remote_path.startswith("/") and not remote_path.startswith("~"):
        remote_path = f"~/{remote_path}"
    dest = local or "."
    cmd = scp_download_cmd(cfg["SSH_HOST"], remote_path, dest, port=cfg["SSH_PORT"], recursive=True)
    return run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(prog=PREFIX, description="SCP 文件传输到/从远程服务器")
    add_env_arg(parser)
    parser.add_argument("action", choices=["upload", "download"], help="传输方向")
    parser.add_argument("src", help="源路径 (upload时为本地路径, download时为远程路径)")
    parser.add_argument("dst", nargs="?", default=None, help="目标路径 (可选)")
    args = parser.parse_args()

    cfg = load_config(args.env)
    if args.action == "upload":
        return upload(cfg, args.src, args.dst)
    return download(cfg, args.src, args.dst)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
