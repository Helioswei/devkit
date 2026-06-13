"""net 模块配置加载。

配置来源优先级:
  1. 命令行 --env 参数指定的 env.py
  2. NET_SSH_HOST / NET_SSH_PORT 环境变量
  3. 模块目录下的 env.py
  4. 默认值 (dev / 22)
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

REPO_ROOT = _MODULE_ROOT


def _load_module_from_path(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None:
        print(f"Error: cannot load module from {path}", file=sys.stderr)
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_config(env_path: str | None = None) -> dict:
    """加载配置，返回 dict 含 SSH_HOST 和 SSH_PORT。"""
    result = {"SSH_HOST": "dev", "SSH_PORT": 22}

    # 1. 加载 env.py（参数指定 或 模块目录默认）
    env_py: Path | None = None
    if env_path:
        env_py = Path(env_path)
        if not env_py.is_file():
            print(f"Error: env file not found: {env_py}", file=sys.stderr)
            sys.exit(1)
    else:
        default_env = REPO_ROOT / "env.py"
        if default_env.is_file():
            env_py = default_env

    if env_py:
        mod = _load_module_from_path(env_py, "_net_env")
        if hasattr(mod, "SSH_HOST"):
            result["SSH_HOST"] = getattr(mod, "SSH_HOST")
        if hasattr(mod, "SSH_PORT"):
            result["SSH_PORT"] = getattr(mod, "SSH_PORT")

    # 2. 环境变量覆盖（优先级最高）
    env_host = os.environ.get("NET_SSH_HOST")
    if env_host:
        result["SSH_HOST"] = env_host
    env_port = os.environ.get("NET_SSH_PORT")
    if env_port:
        result["SSH_PORT"] = int(env_port)

    return result


def add_env_arg(parser):
    """为 argparse 添加 --env 参数。"""
    parser.add_argument(
        "--env",
        help="env.py 配置文件路径（默认: 模块目录下 env.py）",
        default=None,
    )
