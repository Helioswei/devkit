#!/usr/bin/env python3
"""通用 AOSP 镜像部署脚本

用法：python3 core/deploy.py --project <name> [download|deploy|start|setup|verify|all]

从指定步骤开始顺序执行到最后，前一步失败则中止。
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

from pathlib import Path
_MODULE_ROOT = Path(__file__).resolve().parent.parent
_DEVKIT_ROOT = _MODULE_ROOT.parent.parent
sys.path.insert(0, str(_MODULE_ROOT))
sys.path.insert(0, str(_DEVKIT_ROOT / "lib" / "python"))

from core._base import add_project_arg, check_env, get_config, PREFIX
from _ssh import scp_download_cmd
import core.adb_utils
from core.adb_utils import adb, adb_shell, run, wait_for_boot


# ===================== 报告 =====================


class DeployReport:
    def __init__(self):
        self.results = []

    def report(self, label, passed, desc):
        self.results.append((label, passed, desc))
        status = "\033[32mPASS\033[0m" if passed else "\033[31mFAIL\033[0m"
        print(f"  [{label:<5}] {desc:<50} {status}")

    @property
    def total(self):
        return len(self.results)

    @property
    def passed(self):
        return sum(1 for _, p, _ in self.results if p)


# ===================== 步骤 =====================


def step_download(report, cfg):
    remote_zip_path = (
        f"{cfg.REMOTE_PROJECT_PATH}"
        f"/out/target/product/{cfg.PRODUCT_OUT_SUBDIR}/sdk-repo-linux-system-images.zip"
    )
    local_zip = os.path.join(cfg.DOWNLOADS_DIR, "sdk-repo-linux-system-images.zip")
    remote_port = getattr(cfg, "REMOTE_PORT", None)
    scp_cmd = scp_download_cmd(cfg.REMOTE_HOST, remote_zip_path, local_zip, port=remote_port)
    proc = subprocess.Popen(scp_cmd)
    t0 = time.time()
    download_timeout = 1200  # 20 min
    while proc.poll() is None:
        if time.time() - t0 > download_timeout:
            proc.kill()
            proc.wait()
            break
        time.sleep(2)
    elapsed = int(time.time() - t0)
    ok = proc.returncode == 0
    desc = f"scp download ({elapsed}s)"
    if not ok:
        desc += f" (exit={proc.returncode})"
    report.report("DOWN", ok, desc)
    return ok


def step_deploy(report, cfg):
    local_zip = os.path.join(cfg.DOWNLOADS_DIR, "sdk-repo-linux-system-images.zip")
    try:
        result = run(["unzip", "-o", local_zip, "-d", cfg.SDK_IMAGE_BASE], timeout=300)
    except subprocess.TimeoutExpired:
        report.report("DEPLO", False, "unzip timed out (300s)")
        return False
    if result.returncode != 0:
        report.report("DEPLO", False, f"unzip failed (exit={result.returncode})")
        return False
    report.report("DEPLO", True, "unzip + clean overlay")
    return True


_emu_proc = None  # 模拟器进程，用于 wait_for_boot 检测存活


def step_start(report, cfg):
    global _emu_proc

    print("  Killing existing emulator processes...")
    subprocess.run(["pkill", "-9", "-f", "emulator"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", "qemu"], capture_output=True)
    time.sleep(2)

    avd_dir = cfg.AVD_DIR
    for f in glob.glob(os.path.join(avd_dir, "*.qcow2")):
        os.remove(f)
    snapshots_dir = os.path.join(avd_dir, "snapshots")
    if os.path.isdir(snapshots_dir):
        shutil.rmtree(snapshots_dir)

    emulator_cmd = [cfg.EMULATOR, "-avd", cfg.AVD_NAME, "-no-snapshot",
                    "-gpu", "swangle", "-memory", "3072", "-cores", "4"]

    extra_args = cfg.get("EMULATOR_EXTRA_ARGS")
    if extra_args:
        if isinstance(extra_args, str):
            import shlex
            emulator_cmd.extend(shlex.split(extra_args))
        else:
            emulator_cmd.extend(extra_args)

    emu_log = os.path.join(avd_dir, "emulator.log")
    emu_err = open(emu_log, "w")
    _emu_proc = subprocess.Popen(
        emulator_cmd,
        stdout=subprocess.DEVNULL,
        stderr=emu_err,
    )

    time.sleep(5)
    ok, elapsed = wait_for_boot(timeout=120, background_proc=_emu_proc)
    desc = f"emulator boot ({elapsed}s)"
    if not ok:
        desc += f" CRASHED? see {emu_log}"
    report.report("START", ok, desc)
    return ok


def step_setup(report, cfg):
    adb("root")
    time.sleep(2)

    if cfg.has_hook("setup_properties"):
        cfg.call_hook("setup_properties", adb_shell)
    else:
        print("  (no setup_properties hook, skipping property setup)")

    subprocess.Popen([cfg.ADB, "shell", "reboot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)

    ok, elapsed = wait_for_boot(timeout=120, background_proc=_emu_proc)
    if not ok:
        report.report("SETUP", False, f"reboot timeout ({elapsed}s)")
        return False

    time.sleep(5)
    adb("root")
    time.sleep(2)

    if cfg.has_hook("verify_setup"):
        ok = cfg.call_hook("verify_setup", adb_shell)
        desc = f"properties + reboot ({elapsed}s)"
        if not ok:
            desc += " (verify_setup failed)"
    else:
        ok = True
        desc = f"reboot ({elapsed}s), no verify_setup hook"

    report.report("SETUP", ok, desc)
    return ok


def step_verify(report, cfg):
    if cfg.has_hook("verify_environment"):
        ok, desc = cfg.call_hook("verify_environment", adb_shell)
    else:
        boot = adb_shell("getprop", "sys.boot_completed")
        ok = boot.strip() == "1"
        desc = f"boot_completed={boot.strip()}"

    report.report("VERIF", ok, desc)
    return ok


# ===================== 主流程 =====================


STEP_ORDER = ["download", "deploy", "start", "setup", "verify"]

STEP_FN = {
    "download": step_download,
    "deploy": step_deploy,
    "start": step_start,
    "setup": step_setup,
    "verify": step_verify,
}


def main():
    parser = argparse.ArgumentParser(prog=f"{PREFIX} deploy", description="AOSP 镜像部署流水线（下载→解压→启动→配置→验证）")
    add_project_arg(parser)
    parser.add_argument(
        "step", nargs="?", default="all",
        choices=STEP_ORDER + ["all"],
        help="Start from this step (default: all)",
    )
    args = parser.parse_args()

    cfg = get_config(args.project)
    core.adb_utils.init(cfg.ADB)

    if not check_env(cfg, mode="deploy"):
        sys.exit(1)

    start_idx = 0 if args.step == "all" else STEP_ORDER.index(args.step)
    steps_to_run = STEP_ORDER[start_idx:]

    report = DeployReport()
    print(f"\n=== Deploy [{cfg.project_name}] ===\n")

    for step_name in steps_to_run:
        ok = STEP_FN[step_name](report, cfg)
        if not ok:
            print(f"\n  *** {step_name} failed, aborting ***")
            break

    print(f"\n=== Result: {report.passed}/{report.total} PASSED ===\n")


if __name__ == "__main__":
    main()
