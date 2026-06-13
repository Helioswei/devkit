"""仓库路径自发现 + 配置加载。

三层配置：
  1. local.py  — 机器级（ADB 路径、SDK 路径等），gitignore
  2. env.py    — 项目级（服务器、lunch target 等），在 projects/ 或 archive/ 下
  3. 运行时    — --project 参数 或 FW_PROJECT 环境变量
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

from _ssh import is_alias, ssh_cmd, scp_upload_cmd, scp_download_cmd

PREFIX = os.environ.get("DEVKIT_PREFIX", "fw")

REPO_ROOT = _MODULE_ROOT
PROJECTS_DIR = REPO_ROOT / "projects"
ARCHIVE_DIR = REPO_ROOT / "archive"

# ===================== SDK 路径解析 =====================


def _resolve_android_sdk_home(local_mod=None) -> str:
    """解析 Android SDK 根目录。
    优先级：local.py ANDROID_SDK_HOME > ANDROID_HOME env > ANDROID_SDK_ROOT env > 默认值。
    """
    if local_mod and hasattr(local_mod, "ANDROID_SDK_HOME"):
        val = getattr(local_mod, "ANDROID_SDK_HOME")
        if val and val.strip():
            return val
    env_home = os.environ.get("ANDROID_HOME")
    if env_home and env_home.strip():
        return env_home
    env_root = os.environ.get("ANDROID_SDK_ROOT")
    if env_root and env_root.strip():
        return env_root
    return os.path.expanduser("~/Library/Android/sdk")


def _normalize_sdk_image_tag(tag: str) -> str:
    """去掉 SDK_IMAGE_TAG 前后的斜杠，避免路径拼接时出现双斜杠。"""
    return tag.strip("/")


def _make_local_defaults(sdk_home: str, avd_name: str = "Pixel_Tablet", sdk_image_tag: str = "android-36/custom") -> dict:
    """根据 sdk_home、avd_name 和 sdk_image_tag 生成默认机器配置。"""
    tag = _normalize_sdk_image_tag(sdk_image_tag)
    return {
        "ANDROID_SDK_HOME": sdk_home,
        "ADB": os.path.join(sdk_home, "platform-tools", "adb"),
        "EMULATOR": os.path.join(sdk_home, "emulator", "emulator"),
        "SDK_IMAGE_TAG": tag,
        "SDK_IMAGE_BASE": os.path.join(sdk_home, "system-images", tag),
        "AVD_NAME": avd_name,
        "AVD_DIR": os.path.expanduser(f"~/.android/avd/{avd_name}.avd"),
        "DOWNLOADS_DIR": os.path.expanduser("~/Downloads"),
        "LOCAL_SYNC_DIR": "/Volumes/AOSP_Local",
        "SPARSE_IMAGE_PATH": os.path.expanduser("~/AOSP_Dev.sparseimage"),
        "SPARSE_IMAGE_SIZE": "500g",
        "SYNC_NAME": "aosp-sync",
    }


_LOCAL_DEFAULTS = _make_local_defaults(_resolve_android_sdk_home())


# ===================== 模块加载 =====================


def _load_module_from_path(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===================== local.py =====================


def load_local_config() -> dict:
    """加载 local.py；不存在则用默认值。路径从 ANDROID_SDK_HOME 和 AVD_NAME 自动派生。"""
    local_path = REPO_ROOT / "local.py"
    local_mod = None
    if local_path.exists():
        local_mod = _load_module_from_path(local_path, "_fw_local")

    sdk_home = _resolve_android_sdk_home(local_mod)
    avd_name = getattr(local_mod, "AVD_NAME", "Pixel_Tablet") if local_mod else "Pixel_Tablet"
    sdk_image_tag = getattr(local_mod, "SDK_IMAGE_TAG", "android-36/custom") if local_mod else "android-36/custom"
    result = _make_local_defaults(sdk_home, avd_name, sdk_image_tag)

    # local.py 可逐项覆盖默认值（派生项不覆盖，由基值重新计算）
    # 派生项：ANDROID_SDK_HOME, AVD_DIR, SDK_IMAGE_BASE
    derived_keys = {"ANDROID_SDK_HOME", "AVD_DIR", "SDK_IMAGE_BASE"}
    if local_mod:
        for key in result:
            if key not in derived_keys and hasattr(local_mod, key):
                result[key] = getattr(local_mod, key)
        if hasattr(local_mod, "ANDROID_SDK_HOME"):
            result["ANDROID_SDK_HOME"] = getattr(local_mod, "ANDROID_SDK_HOME")
        # AVD_NAME 改变后重新派生 AVD_DIR
        if hasattr(local_mod, "AVD_NAME"):
            result["AVD_NAME"] = getattr(local_mod, "AVD_NAME")
            result["AVD_DIR"] = os.path.expanduser(f"~/.android/avd/{result['AVD_NAME']}.avd")
        # SDK_IMAGE_TAG 改变后重新派生 SDK_IMAGE_BASE
        if hasattr(local_mod, "SDK_IMAGE_TAG"):
            result["SDK_IMAGE_TAG"] = getattr(local_mod, "SDK_IMAGE_TAG")
            result["SDK_IMAGE_BASE"] = os.path.join(result["ANDROID_SDK_HOME"], "system-images", result["SDK_IMAGE_TAG"])

    return result


# ===================== 项目解析 =====================


def _find_project_dir(name: str) -> Path:
    """在 projects/ 和 archive/ 中查找项目目录。projects/ 优先，同名时打印提示。"""
    found = None
    for base in (PROJECTS_DIR, ARCHIVE_DIR):
        candidate = base / name
        if candidate.is_dir() and (candidate / "env.py").exists():
            if found is not None:
                label_kept = "projects" if found.parent == PROJECTS_DIR else "archive"
                label_skip = "projects" if base == PROJECTS_DIR else "archive"
                if name not in _conflict_notes_printed:
                    print(f"  Note: '{name}' exists in both {label_kept}/ and {label_skip}/, "
                          f"using {label_kept}/", file=sys.stderr)
                    _conflict_notes_printed.add(name)
                continue
            found = candidate

    if found is not None:
        return found
    available = _list_available_projects()
    if available:
        hint = f"Available: {', '.join(available)}"
    else:
        hint = "No projects yet. Create one: mkdir -p projects/<name> && add env.py"
    raise FileNotFoundError(
        f"Project '{name}' not found. {hint}\n"
        f"  Looked in:\n"
        f"    {PROJECTS_DIR / name}/env.py\n"
        f"    {ARCHIVE_DIR / name}/env.py"
    )


# 记录已打印的同名冲突提示，避免重复
_conflict_notes_printed: set = set()


def _list_available_projects() -> list[str]:
    """列出所有可用项目名（去重，projects/ 优先）。"""
    seen = []
    seen_names = set()
    for base in (PROJECTS_DIR, ARCHIVE_DIR):
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if d.is_dir() and (d / "env.py").exists() and d.name not in seen_names:
                    seen.append(d.name)
                    seen_names.add(d.name)
    return seen


def resolve_project(name: str | None = None) -> str:
    """解析当前项目名。优先级：参数 > FW_PROJECT 环境变量 > 自动选中（仅一个项目时）> 报错。"""
    if name:
        return name
    env_val = os.environ.get("FW_PROJECT")
    if env_val:
        return env_val

    available = _list_available_projects()

    # 只有一个项目时自动选中
    if len(available) == 1:
        auto = available[0]
        print(f"  Auto-selected project: {auto} (only one available)", file=sys.stderr)
        return auto

    # 零个项目时引导创建
    if len(available) == 0:
        print("Error: No projects found.", file=sys.stderr)
        print("  Create your first project:", file=sys.stderr)
        print(f"    {PREFIX} create <project_name>", file=sys.stderr)
        sys.exit(1)

    # 多个项目时报错并给出具体命令
    print("Error: No project specified, multiple projects available.", file=sys.stderr)
    print("  Choose one:", file=sys.stderr)
    for p in available:
        print(f"    export FW_PROJECT={p}", file=sys.stderr)
    print(f"  Or use: {PREFIX} <command> -p <name>", file=sys.stderr)
    sys.exit(1)


def load_project_env(project_name: str) -> ModuleType:
    """加载项目的 env.py 模块。"""
    project_dir = _find_project_dir(project_name)
    return _load_module_from_path(project_dir / "env.py", f"_fw_env_{project_name}")


# ===================== 统一配置 =====================


class Config:
    """合并 local + project 配置的统一访问对象。"""

    def __init__(self, project_name: str):
        self._local = load_local_config()
        self._env = load_project_env(project_name)
        self.project_dir = _find_project_dir(project_name)

        # 优先 env.py PROJECT_NAME；无则用目录名
        env_project_name = getattr(self._env, "PROJECT_NAME", None)
        if env_project_name and env_project_name.strip():
            self.project_name = env_project_name
        else:
            self.project_name = project_name

    def __getattr__(self, name):
        if name.startswith("_") or name in ("project_name", "project_dir"):
            raise AttributeError(name)
        # 先查项目 env，再查 local
        if hasattr(self._env, name):
            return getattr(self._env, name)
        if name in self._local:
            return self._local[name]
        raise AttributeError(f"Config has no attribute '{name}' (checked env.py and local.py)")

    def get(self, name, default=None):
        try:
            return getattr(self, name)
        except AttributeError:
            return default

    def has_hook(self, name: str) -> bool:
        """检查项目 env.py 是否定义了指定的 hook 函数。"""
        return callable(getattr(self._env, name, None))

    def call_hook(self, name: str, *args, **kwargs):
        """调用项目 env.py 中定义的 hook 函数。"""
        fn = getattr(self._env, name, None)
        if callable(fn):
            return fn(*args, **kwargs)
        return None


def get_local_config() -> dict:
    """只加载 local.py 配置，不需要项目 env.py。用于 sync 等非项目级命令。"""
    return load_local_config()


def get_config(project_name: str | None = None) -> Config:
    """获取完整配置。project_name 可由参数、环境变量提供。"""
    name = resolve_project(project_name)
    return Config(name)


# ===================== argparse 通用参数 =====================


def add_project_arg(parser: argparse.ArgumentParser):
    """为 argparse 添加 --project 参数。"""
    parser.add_argument(
        "--project", "-p",
        help="Project name (or set FW_PROJECT env var)",
        default=None,
    )


# ===================== 环境检测 =====================


def check_ssh_connectivity(remote_host: str, remote_port: int | None = None, timeout: int = 10) -> tuple[bool, str]:
    """检查 SSH 连通性。返回 (ok, fix_hint)。ok=True 表示连通，fix_hint 为空。
    ok=False 时 fix_hint 提供修复建议。"""
    _ssh_cmd = ssh_cmd(remote_host, "echo ok", port=remote_port)
    try:
        result = subprocess.run(_ssh_cmd, capture_output=True, timeout=timeout, text=True)
    except subprocess.TimeoutExpired:
        return False, "SSH: timeout connecting to {remote_host} — check network or SSH config"
    except FileNotFoundError:
        return False, "SSH: ssh binary not found — install OpenSSH client"

    if result.returncode != 0 or result.stdout.strip() != "ok":
        if is_alias(remote_host):
            fix_hint = (
                f"检查 ~/.ssh/config 是否定义了 '{remote_host}'，"
                f"或改用 user@ip 格式设置 REMOTE_HOST"
            )
        else:
            fix_hint = "检查网络连通性，或设置 REMOTE_PORT（如端口非 22）"
        return False, f"SSH: cannot connect to {remote_host}\n  Fix: {fix_hint}"
    return True, ""


def check_env(cfg: Config, mode: str = "all") -> bool:
    """检测必要工具和目录是否存在。返回 True 表示全部通过。

    mode: "build" 检查 SSH 连通；"deploy" 检查 ADB/emulator/SDK 目录；"all" 检查全部。
    """
    errors = []

    def _check_binary(path, label, fix_hint):
        if not os.path.isfile(path):
            errors.append(f"{label}: binary not found at {path}\n  Fix: {fix_hint}")
            return False
        if not os.access(path, os.X_OK):
            errors.append(f"{label}: not executable at {path}\n  Fix: chmod +x {path}")
            return False
        return True

    def _check_dir(path, label, fix_hint):
        if not Path(path).is_dir():
            errors.append(f"{label}: directory not found at {path}\n  Fix: {fix_hint}")
            return False
        return True

    checks = []

    if mode in ("deploy", "all"):
        checks.append(_check_binary(
            cfg.ADB, "ADB",
            "Set ANDROID_SDK_HOME in local.py or set ANDROID_HOME env var to your SDK root.",
        ))
        checks.append(_check_binary(
            cfg.EMULATOR, "Emulator",
            "Set ANDROID_SDK_HOME in local.py or install emulator via sdkmanager.",
        ))
        checks.append(_check_dir(
            cfg.SDK_IMAGE_BASE, "SDK images dir",
            f"mkdir -p {cfg.SDK_IMAGE_BASE}",
        ))

    if mode in ("build", "all"):
        remote_host = getattr(cfg, "REMOTE_HOST", None)
        if remote_host:
            remote_port = getattr(cfg, "REMOTE_PORT", None)
            ok, hint = check_ssh_connectivity(remote_host, remote_port)
            if not ok:
                errors.append(hint)
                checks.append(False)
            else:
                checks.append(True)

    checks.append(_check_dir(
        cfg.DOWNLOADS_DIR, "Downloads dir",
        f"mkdir -p {cfg.DOWNLOADS_DIR}",
    ))

    all_ok = all(checks)
    if not all_ok:
        print("\n=== Environment check FAILED ===\n", file=sys.stderr)
        for e in errors:
            print(f"  {e}\n", file=sys.stderr)
        print(f"  Run '{PREFIX} doctor' for a full environment report.\n", file=sys.stderr)

    return all_ok
