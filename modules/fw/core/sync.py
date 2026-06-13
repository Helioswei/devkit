#!/usr/bin/env python3
"""代码同步工具 — Mutagen + 稀疏镜像自动化管理。

用法：
  fw sync start [-p project]   # 自动：创建镜像→挂载→创建同步（缺什么做什么）
  fw sync pause  [-p project]  # 暂停同步（不需要 -p）
  fw sync resume [-p project]  # 恢复同步（不需要 -p）
  fw sync status               # 查看同步状态（不需要 -p）
  fw sync stop   [-p project]  # 终止同步 + 卸载镜像（不需要 -p）

start 需要 -p 来确定远程服务器地址；其他操作只用 local.py 配置。
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

from core._base import add_project_arg, get_config, get_local_config, REPO_ROOT, PREFIX
from _run import run_check


def _check_mounted(mount_point):
    """检查镜像是否已挂载。"""
    result = subprocess.run(["hdiutil", "info"], capture_output=True, text=True)
    return mount_point in result.stdout


def _find_session(sync_name):
    """查找 mutagen 同步会话，返回 (exists, paused)。"""
    result = subprocess.run(["mutagen", "sync", "list"], capture_output=True, text=True)
    if result.returncode != 0:
        return False, False
    lines = result.stdout.split("\n")
    for idx, line in enumerate(lines):
        if sync_name in line:
            for i in range(idx, min(idx + 5, len(lines))):
                if "Paused" in lines[i]:
                    return True, True
            return True, False
    return False, False


def sync_start(cfg):
    """自动全做：缺镜像→创建，缺挂载→挂载，缺同步→创建。"""
    image_path = cfg.SPARSE_IMAGE_PATH
    image_size = cfg.SPARSE_IMAGE_SIZE
    mount_point = cfg.LOCAL_SYNC_DIR
    sync_name = cfg.SYNC_NAME
    remote_host = cfg.REMOTE_HOST
    remote_path = cfg.REMOTE_PROJECT_PATH
    config_file = str(REPO_ROOT / "aosp-sync.yml")

    # 1. 检查 mutagen 是否安装
    if subprocess.run(["which", "mutagen"], capture_output=True).returncode != 0:
        print("Error: mutagen not found.", file=sys.stderr)
        print("  Install: brew install mutagen-io/mutagen/mutagen", file=sys.stderr)
        sys.exit(1)
    print("  mutagen: installed")

    # 2. 稀疏镜像
    if not os.path.isfile(image_path):
        print(f"  Creating sparse image: {image_path} ({image_size})")
        run_check([
            "hdiutil", "create",
            "-size", image_size,
            "-type", "SPARSE",
            "-fs", "Case-sensitive APFS",
            "-volname", os.path.basename(mount_point).replace("_", " "),
            image_path,
        ], label="Create sparse image")
        print("  Sparse image created")
    else:
        print(f"  Sparse image: {image_path} (exists)")

    # 3. 挂载
    if not _check_mounted(mount_point):
        print(f"  Mounting: {image_path} → {mount_point}")
        run_check(["hdiutil", "attach", image_path], label="Mount sparse image")
        print(f"  Mounted at {mount_point}")
    else:
        print(f"  Already mounted at {mount_point}")

    # 4. 同步会话
    exists, paused = _find_session(sync_name)
    if not exists:
        print(f"  Creating sync session: {sync_name}")
        print(f"    Local:  {mount_point}")
        print(f"    Remote: {remote_host}:{remote_path}")
        run_check([
            "mutagen", "sync", "create",
            "--name", sync_name,
            "--configuration-file", config_file,
            mount_point,
            f"{remote_host}:{remote_path}",
        ], label="Create mutagen sync")
        print(f"  Sync session created: {sync_name}")
    elif paused:
        print(f"  Resuming paused session: {sync_name}")
        run_check(["mutagen", "sync", "resume", sync_name], label="Resume mutagen sync")
        print(f"  Sync resumed: {sync_name}")
    else:
        print(f"  Sync already running: {sync_name}")

    print("\n  All ready! Code is syncing between local and remote.")


def sync_pause(cfg):
    """暂停同步。"""
    run_check(["mutagen", "sync", "pause", cfg.SYNC_NAME], label="Pause sync")
    print(f"  Sync paused: {cfg.SYNC_NAME}")


def sync_resume(cfg):
    """恢复同步。"""
    run_check(["mutagen", "sync", "resume", cfg.SYNC_NAME], label="Resume sync")
    print(f"  Sync resumed: {cfg.SYNC_NAME}")


def sync_status(cfg):
    """查看同步状态。"""
    result = subprocess.run(["mutagen", "sync", "list"], capture_output=True, text=True)
    print(result.stdout)


def sync_stop(cfg):
    """终止同步 + 卸载镜像。"""
    sync_name = cfg.SYNC_NAME
    image_path = cfg.SPARSE_IMAGE_PATH
    mount_point = cfg.LOCAL_SYNC_DIR

    # 终止同步
    if _find_session(sync_name)[0]:
        print(f"  Terminating sync: {sync_name}")
        run_check(["mutagen", "sync", "terminate", sync_name], label="Terminate sync")
        print(f"  Sync terminated: {sync_name}")
    else:
        print(f"  Sync session not found: {sync_name}")

    # 卸载镜像
    if _check_mounted(mount_point):
        print(f"  Detaching: {mount_point}")
        run_check(["hdiutil", "detach", mount_point], label="Detach image")
        print(f"  Image detached")
    else:
        print(f"  Image not mounted")


# start 需要项目配置（REMOTE_HOST），其他操作只用 local.py
NEED_PROJECT = {"start"}
ACTIONS = {
    "start": sync_start,
    "pause": sync_pause,
    "resume": sync_resume,
    "status": sync_status,
    "stop": sync_stop,
}


class _LocalCfg:
    """用 local.py dict 模拟 Config 对象，用于不需要项目的 sync 操作。"""
    def __init__(self, local_dict):
        self._data = local_dict
        self.project_name = "local"

    def __getattr__(self, name):
        if name.startswith("_") or name in ("project_name", "project_dir"):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Local config has no attribute '{name}'")


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} sync", description="Mutagen 代码同步管理（创建→暂停→恢复→状态→终止）")
    add_project_arg(parser)
    parser.add_argument(
        "action", choices=list(ACTIONS.keys()),
        help="Action: start (auto setup, needs -p), pause, resume, status, stop",
    )
    args = parser.parse_args()

    if args.action in NEED_PROJECT:
        cfg = get_config(args.project)
    else:
        cfg = _LocalCfg(get_local_config())

    print(f"\n=== Sync [{cfg.project_name}] ===\n")
    ACTIONS[args.action](cfg)


if __name__ == "__main__":
    main()
