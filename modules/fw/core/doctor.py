#!/usr/bin/env python3
"""环境诊断工具 — 检查 frameworkflow 所需依赖是否就绪。

用法：fw doctor [-p project]
"""

import argparse
import os
import sys

from pathlib import Path
_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

from core._base import add_project_arg, get_config, _list_available_projects, _find_project_dir, REPO_ROOT, load_local_config, check_ssh_connectivity, PREFIX
from _ssh import is_alias

COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"
COLOR_RESET = "\033[0m"


def _status(ok, label, detail="", fix=""):
    """打印一行状态。"""
    mark = f"{COLOR_GREEN}OK{COLOR_RESET}" if ok else f"{COLOR_RED}MISSING{COLOR_RESET}"
    line = f"  {mark}  {label}"
    if detail:
        line += f"  ({detail})"
    if not ok and fix:
        line += f"\n       {COLOR_YELLOW}Fix: {fix}{COLOR_RESET}"
    print(line)
    return ok


def doctor(cfg=None):
    """运行全部环境检查并报告状态。"""
    results = []

    # 1. local.py 存在
    local_path = REPO_ROOT / "local.py"
    local_exists = local_path.exists()
    results.append(_status(
        local_exists, "local.py",
        detail=str(local_path) if local_exists else "not found",
        fix="cp local.py.example local.py && edit ANDROID_SDK_HOME if needed",
    ))

    # 2. local.py 配置项（统一用 OK/MISSING 格式）
    if local_exists:
        try:
            local_dict = load_local_config()
            # 项目检查会覆盖的 key 不重复显示
            checked_keys = {"ANDROID_SDK_HOME", "ADB", "EMULATOR", "SDK_IMAGE_BASE", "DOWNLOADS_DIR"}
            skip_keys = checked_keys if cfg is not None else set()
            for key, val in local_dict.items():
                if key not in skip_keys:
                    results.append(_status(True, key, detail=val))
        except Exception as e:
            results.append(_status(False, "local.py config", detail=str(e),
                                   fix="Check local.py for syntax errors"))
    else:
        results.append(_status(False, "local.py config", detail="skipped (no local.py)"))

    # 3. FW_PROJECT 环境变量
    fw_project = os.environ.get("FW_PROJECT")
    available = _list_available_projects()

    if fw_project:
        # 验证 FW_PROJECT 是否指向有效项目
        try:
            from core._base import _find_project_dir
            project_dir = _find_project_dir(fw_project)
            results.append(_status(
                True, "FW_PROJECT env",
                detail=f"{fw_project} → {project_dir}",
            ))
        except FileNotFoundError:
            results.append(_status(
                False, "FW_PROJECT env",
                detail=f"{fw_project} (project not found)",
                fix=f"Valid projects: {', '.join(available)}",
            ))
    elif available:
        results.append(_status(
            False, "FW_PROJECT env",
            detail=f"not set, available: {', '.join(available)}",
            fix=f"export FW_PROJECT={available[0]} (optional, avoids -p flag every time)",
        ))
    else:
        results.append(_status(
            False, "FW_PROJECT env",
            detail="not set, no projects yet",
            fix=f"{PREFIX} create <name> to create your first project",
        ))

    # 无 project 时跳过项目级检查
    if cfg is None:
        print("\n  (Project-dependent checks skipped -- use -p <project> or set FW_PROJECT)\n")
        return all(results)

    print(f"\n  Project: {cfg.project_name}\n")

    # 4. ANDROID_SDK_HOME / SDK 根目录
    sdk_home = cfg.get("ANDROID_SDK_HOME")
    results.append(_status(
        os.path.isdir(sdk_home) if sdk_home else False,
        "ANDROID_SDK_HOME",
        detail=sdk_home or "not resolved",
        fix="Set ANDROID_SDK_HOME in local.py or ANDROID_HOME env var",
    ))

    # 5. ADB 二进制
    adb_path = cfg.ADB
    adb_ok = os.path.isfile(adb_path) and os.access(adb_path, os.X_OK)
    results.append(_status(
        adb_ok, "ADB binary",
        detail=adb_path,
        fix="Set ANDROID_SDK_HOME in local.py or ANDROID_HOME env var to your SDK root",
    ))

    # 6. Emulator 二进制
    emu_path = cfg.EMULATOR
    emu_ok = os.path.isfile(emu_path) and os.access(emu_path, os.X_OK)
    results.append(_status(
        emu_ok, "Emulator binary",
        detail=emu_path,
        fix="Install emulator via sdkmanager or set ANDROID_SDK_HOME in local.py",
    ))

    # 7. SDK images 目录
    sdk_dir = cfg.SDK_IMAGE_BASE
    results.append(_status(
        os.path.isdir(sdk_dir), "SDK images dir",
        detail=sdk_dir,
        fix=f"mkdir -p {sdk_dir}",
    ))

    # 8. Downloads 目录
    dl_dir = cfg.DOWNLOADS_DIR
    results.append(_status(
        os.path.isdir(dl_dir), "Downloads dir",
        detail=dl_dir,
        fix=f"mkdir -p {dl_dir}",
    ))

    # 9. SSH 连通性
    remote_host = getattr(cfg, "REMOTE_HOST", None)
    remote_port = getattr(cfg, "REMOTE_PORT", None)
    if remote_host:
        # alias + REMOTE_PORT 冗余提示（信息性，不影响诊断结果）
        if is_alias(remote_host) and remote_port is not None:
            print(f"  {COLOR_YELLOW}注意: REMOTE_HOST 是 SSH alias ({remote_host})，"
                  f"端口由 ~/.ssh/config 决定，REMOTE_PORT={remote_port} 将被忽略。{COLOR_RESET}")
        ssh_ok, ssh_hint = check_ssh_connectivity(remote_host, remote_port)
        if ssh_ok:
            results.append(_status(True, "SSH connectivity", detail=f"ssh {remote_host}"))
        else:
            results.append(_status(False, "SSH connectivity",
                                   detail=f"ssh {remote_host}",
                                   fix=ssh_hint.split("\n  Fix: ")[-1] if "Fix:" in ssh_hint else ssh_hint))
    else:
        results.append(_status(False, "SSH host", detail="REMOTE_HOST not set in env.py"))

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"\n  Summary: {passed}/{total} checks passed\n")

    return all(results)


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} doctor", description=f"环境诊断 — 检查 {PREFIX} 所需依赖是否就绪")
    add_project_arg(parser)
    args = parser.parse_args()

    print(f"\n=== {PREFIX} doctor ===\n")

    cfg = None
    if args.project:
        cfg = get_config(args.project)

    ok = doctor(cfg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
