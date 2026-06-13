#!/usr/bin/env python3
"""项目创建工具 — 快速创建项目目录和 env.py 模板。

用法：fw create <project_name>
"""

import argparse
import os
import sys

from pathlib import Path
_MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_MODULE_ROOT))

from core._base import PROJECTS_DIR, ARCHIVE_DIR, _list_available_projects, PREFIX

ENV_TEMPLATE = '''"""{name} 项目环境配置"""

PROJECT_NAME = "{name}"

# ===================== 远程构建环境 =====================

# REMOTE_HOST 三种格式均可:
#   "dev"                       — SSH alias（需 ~/.ssh/config 配置，端口也在其中定义）
#   "build@192.168.1.100"       — user@ip（无需 ~/.ssh/config）
#   "192.168.1.100"             — 纯 ip（用当前系统用户名）
REMOTE_HOST = "dev"
REMOTE_PORT = 22                # 可选，默认 22。alias 格式下此值被忽略（端口由 ~/.ssh/config 决定）
REMOTE_PROJECT_PATH = "/workspace/projects/android16_aosp"
LUNCH_TARGET = "sdk_car_arm64-trunk_staging-userdebug"
PRODUCT_OUT_SUBDIR = "emulator_car64_arm64"

# ===================== 部署 Hook（按需实现） =====================


def setup_properties(adb_shell):
    """设置项目需要的属性。"""
    pass


def verify_setup(adb_shell):
    """验证属性是否设置正确。"""
    return True


def verify_environment(adb_shell):
    """验证部署环境。返回 (ok, description)。"""
    boot = adb_shell("getprop", "sys.boot_completed")
    ok = boot.strip() == "1"
    return ok, f"boot_completed={boot.strip()}"
'''


def create_project(name: str) -> None:
    """创建项目目录和 env.py 模板。"""
    project_dir = PROJECTS_DIR / name

    # 检查项目名是否已存在
    if project_dir.is_dir() and (project_dir / "env.py").exists():
        print(f"Error: project '{name}' already exists at {project_dir}/", file=sys.stderr)
        sys.exit(1)

    archive_dir = ARCHIVE_DIR / name
    if archive_dir.is_dir() and (archive_dir / "env.py").exists():
        print(f"Warning: '{name}' already exists in archive/ ({archive_dir}/).", file=sys.stderr)
        print(f"  If you want to restore it, use: {PREFIX} archive -p {name}  (then choose merge)", file=sys.stderr)
        sys.exit(1)

    # 创建目录和 env.py
    project_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    env_path = project_dir / "env.py"
    env_content = ENV_TEMPLATE.replace("{name}", name)
    env_path.write_text(env_content)

    print(f"  Created: {project_dir}/env.py")
    print(f"  Created: {docs_dir}/")
    print(f"\n  Next steps:")
    print(f"    1. Edit env.py: {env_path}")
    print(f"    2. Set REMOTE_HOST, REMOTE_PROJECT_PATH, LUNCH_TARGET etc.")
    print(f"    3. Run: export FW_PROJECT={name}")
    print(f"    4. Run: {PREFIX} doctor -p {name}")
    print(f"    5. Run: {PREFIX} build -p {name}")


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} create", description="创建新项目（生成 env.py 模板）")
    parser.add_argument("name", help="Project name (will create projects/<name>/env.py)")
    args = parser.parse_args()

    create_project(args.name)


if __name__ == "__main__":
    main()
