#!/usr/bin/env python3
"""通用 AOSP 远程编译脚本

用法：
  python3 core/build.py --project <name>                  # 全量编译 + 打包
  python3 core/build.py --project <name> --module framework-minus-apex
  python3 core/build.py --project <name> --dry-run        # 只打印命令不执行
"""

import argparse
import os
import subprocess
import sys

from pathlib import Path
_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

from core._base import add_project_arg, check_env, get_config, PREFIX
from _ssh import ssh_cmd


def build_ssh_command(cfg, module=None):
    """构造 SSH 编译命令。"""
    remote_path = cfg.REMOTE_PROJECT_PATH
    lunch_target = cfg.LUNCH_TARGET

    if module:
        build_cmd = f"m -j24 {module}"
    else:
        build_cmd = "m && make emu_img_zip"

    full_cmd = (
        f"cd {remote_path} && "
        f"source build/envsetup.sh && "
        f"lunch {lunch_target} && "
        f"{build_cmd}"
    )
    remote_host = cfg.REMOTE_HOST
    if not remote_host:
        print("Error: REMOTE_HOST not set in env.py", file=sys.stderr)
        sys.exit(1)
    remote_port = getattr(cfg, "REMOTE_PORT", None)
    return ssh_cmd(remote_host, full_cmd, port=remote_port)


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} build", description="AOSP 远程编译（全量或指定模块）")
    add_project_arg(parser)
    parser.add_argument("--module", "-m", help="Build specific module instead of full build")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
    args = parser.parse_args()

    cfg = get_config(args.project)
    if not check_env(cfg, mode="build"):
        sys.exit(1)
    cmd = build_ssh_command(cfg, module=args.module)

    print(f"\n=== Build [{cfg.project_name}] ===\n")
    print(f"  Host:   {cfg.REMOTE_HOST}")
    print(f"  Path:   {cfg.REMOTE_PROJECT_PATH}")
    print(f"  Target: {cfg.LUNCH_TARGET}")
    print(f"  Module: {args.module or '(full build + emu_img_zip)'}")
    print(f"  Command: {' '.join(cmd)}\n")

    if args.dry_run:
        print("  [DRY RUN] Command not executed.")
        return

    try:
        result = subprocess.run(cmd, timeout=7200)
    except subprocess.TimeoutExpired:
        print("\nError: build timed out (2h limit).SSH 连接可能已断开。", file=sys.stderr)
        sys.exit(1)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
