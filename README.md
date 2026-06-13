# devkit — 统一开发者工具包

> 一个命令跨机器同步的开发工具集。5 个模块，按需安装，共享基础设施。

## 快速开始

```bash
# 交互式安装（选择需要的模块）
bash install.sh

# 或直接安装某个模块
bash modules/fw/install.sh
bash modules/log/install.sh
```

安装完成后重启终端，或 `source ~/.aliases` 即可使用。

## 模块概览

| 模块 | 类型 | 说明 | 命令示例 |
|------|------|------|----------|
| **fw** | python | AOSP 远程编译 + 镜像部署 + 代码同步 | `devkit fw build -p effect`, `devkit fw doctor` |
| **log** | python | 日志解析 + 正则文本过滤 | `devkit log wms *.log`, `devkit log keep <pattern> <file>` |
| **net** | python | SCP 文件传输 + 局域网存活扫描 | `devkit net up <file>`, `devkit net scan -t 2` |
| **video** | python | ffmpeg 视频合并（片头片尾 + 文字水印） | `devkit video config.txt` |
| **vim** | config | Vim C++ 开发配置（插件 + astyle + ctags） | 安装后自动生效 |

## 各模块用法

### fw — AOSP 开发流程

```bash
devkit fw build   [-m module] [-p project] [--dry-run]   # 远程编译
devkit fw deploy  [step] [-p project]                     # 镜像部署流水线
devkit fw doctor  [-p project]                            # 环境诊断
devkit fw create  <project_name>                          # 创建项目
devkit fw archive [-p project]                            # 归档项目
devkit fw sync    <start|pause|resume|status|stop>        # 代码同步
```

**项目配置**: `devkit fw create <name>` 生成 `projects/<name>/env.py`，定义 `REMOTE_HOST`、`LUNCH_TARGET` 等。

**机器配置**: 复制 `local.py.example` 为 `local.py`，设置 `ANDROID_SDK_HOME` 等（gitignore 不提交）。

**HOST 格式**:
- `"dev"` — SSH config alias（端口由 `~/.ssh/config` 决定）
- `"build@192.168.1.100"` — user@ip（按需加 `-p port`）
- `"192.168.1.100"` — 纯 IP（用当前用户名，按需加 `-p port`）

**项目选择**: `devkit fw build -p effect` 或设环境变量 `export FW_PROJECT=effect` 跳过 `-p`。

### log — 日志解析

```bash
devkit log parse   (p)   <subsystem> <files>   # 保留匹配行（wms, rvc, str 等）
devkit log delete  (d)   <subsystem> <files>   # 删除匹配行（fusion, layout）
devkit log list    (l)                         # 列出所有子系统
devkit log keep    (k)   <file> <pattern>      # 保留匹配行 → *.filter
devkit log keep-any(ka)  <file> <patterns>     # 保留匹配任一 → *.filter
devkit log remove  (r)   <file> <pattern>      # 删除匹配行 → *.del
devkit log remove-any(ra) <file> <patterns>    # 删除匹配任一 → *.del
devkit log range         <file> <start> <end>  # 提取行范围 → *.line
```

### net — 文件传输

```bash
devkit net up     <local> [remote]             # SCP 上传
devkit net down   <remote> [local]             # SCP 下载
devkit net scan   [-t timeout] [-o output]     # 局域网扫描
```

SSH 目标可通过环境变量配置:
```bash
export NET_SSH_HOST=dev          # 默认 "dev"
export NET_SSH_PORT=28225        # 默认 28225（alias 格式下端口由 ssh config 决定）
```

### video — 视频合并

```bash
devkit video [config.txt]               # 默认读取 config.txt
```

配置文件格式:
```
author=作者名
intro=片头秒数
outro=片尾秒数
视频文件|标题|开始秒|结束秒
```

参见 `config.txt.example`。

## 添加新模块

只需三步，零代码改动：

1. 创建 `modules/<name>/` 目录
2. 添加 `module.yml`:
   ```yaml
   name: mymod
   description: "模块说明"
   install: install.sh
   type: python        # 或 config
   category: util
   ```
3. 编写 `install.sh`（python 模块用 `install_alias devkit`，config 模块用 symlink）

顶层 `install.sh` 自动扫描 `modules/*/module.yml` 发现新模块。

## 架构

```
devkit/
  devkit                 # 统一入口 dispatcher（设置 DEVKIT_PREFIX，转发到模块）
  install.sh              # 交互式安装入口
  lib/
    install_utils.sh      # Bash 共享函数（颜色、OS检测、包安装、alias）
    python/
      _ssh.py             # SSH/SCP 命令构造（alias 检测 + 端口标志）
      _run.py             # 子进程助手（run 流式输出, run_check 捕获+失败退出）
  modules/
    fw/                   # Bash dispatcher → core/*.py + projects/ + archive/
    log/                  # Bash dispatcher → core/_log.py, core/_filter.py
    net/                  # Bash dispatcher → core/_transfer.py, core/_network.py
    video/                # Bash dispatcher → core/_merge.py
    vim/                  # .vimrc + shell 脚本（symlink 安装）
```

**统一入口模式** — 所有命令通过 `devkit` 入口转发:
```bash
# devkit dispatcher: 设置 DEVKIT_PREFIX，转发到模块 dispatcher
export DEVKIT_PREFIX="devkit"
case "$1" in
  fw|net|log|video)  exec "$REPO_ROOT/modules/$1/$1" "${@:2}" ;;
esac
```

**Bash dispatcher 模式** — 模块级子命令路由:
```bash
PREFIX="${DEVKIT_PREFIX:-fw}"   # 通过 devkit 入口时为 "devkit fw"，单独运行时为 "fw"
case "$1" in
  cmd|c)  python3 "$REPO_ROOT/core/_script.py" "${@:2}" ;;
  *)      ... ;;
esac
```

**Python 导入模式** — 需要共享库的脚本:
```python
_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))                    # from core.xxx
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python")) # from _ssh, _run
```

## 依赖

| 模块 | 必需 |
|------|------|
| fw | python3 ≥ 3.8, SSH, adb, emulator, mutagen (sync) |
| log | python3 ≥ 3.8, grep |
| net | python3 ≥ 3.8, scp/ssh, ping |
| video | python3 ≥ 3.8, ffmpeg, ffprobe |
| vim | vim ≥ 8, clang-format/astyle, ctags |

macOS 用户推荐 Homebrew 安装: `brew install mutagen-io/mutagen/mutagen ffmpeg`

## 环境要求

- macOS 或 Linux
- Python 3.8+
- Bash / Zsh
