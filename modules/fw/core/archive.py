#!/usr/bin/env python3
"""项目归档工具 — 将 projects/ 下的项目移至 archive/。

用法：fw archive -p <name>
"""

import argparse
import shutil
import sys

from pathlib import Path
_MODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_MODULE_ROOT))

from core._base import add_project_arg, resolve_project, PROJECTS_DIR, ARCHIVE_DIR, PREFIX


def archive_project(name: str) -> None:
    """将项目从 projects/ 归档到 archive/。"""
    src = PROJECTS_DIR / name
    dst = ARCHIVE_DIR / name

    # 检查源目录存在
    if not src.is_dir() or not (src / "env.py").exists():
        print(f"Error: project '{name}' not found in projects/.", file=sys.stderr)
        sys.exit(1)

    # 确保 archive/ 目录存在
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if dst.is_dir():
        print(f"  Archive '{name}' → archive/{name}/")
        print(f"  Warning: archive/{name}/ already exists.\n")
        print("  Choose:")
        print("    1) Overwrite — delete old archive, replace with current project")
        print("    2) Merge    — current project files overwrite archive, archive-only files kept")
        print("    3) Cancel   — do nothing\n")

        choice = input("  Enter choice (1/2/3): ").strip()

        if choice == "1":
            shutil.rmtree(dst)
            shutil.move(str(src), str(dst))
            print(f"\n  Overwritten: archive/{name}/")
        elif choice == "2":
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            shutil.rmtree(src)
            print(f"\n  Merged: archive/{name}/ (archive-only files preserved)")
        else:
            print("\n  Cancelled. No changes made.")
            return
    else:
        shutil.move(str(src), str(dst))
        print(f"\n  Archived: {name} → archive/{name}/")

    print(f"  Source removed: projects/{name}/")
    print(f"  Archive location: {dst}/")


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} archive", description="将项目从 projects/ 归档到 archive/")
    add_project_arg(parser)
    args = parser.parse_args()

    name = resolve_project(args.project)
    archive_project(name)


if __name__ == "__main__":
    main()
