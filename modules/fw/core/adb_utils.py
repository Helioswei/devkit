"""ADB 工具函数 — 所有项目共享。

使用前必须调用 init(adb_path) 初始化，通常为 cfg.ADB。
"""

import subprocess
import sys
import threading
import time


class AdbRunner:
    """封装 ADB 二进制路径，提供 adb 命令辅助函数。"""

    def __init__(self, adb_path: str):
        self.adb_path = adb_path

    def run(self, cmd, timeout=None, shell=False):
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=shell
        )

    def run_live(self, cmd, timeout=None):
        """Run command streaming stdout/stderr to terminal in real time."""
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_parts = []
        stderr_parts = []

        def stream(fd, parts, terminal):
            while True:
                chunk = fd.read(1)
                if not chunk:
                    break
                parts.append(chunk)
                if terminal:
                    terminal.buffer.write(chunk)
                    terminal.buffer.flush()
            fd.close()

        t_out = threading.Thread(target=stream, args=(proc.stdout, stdout_parts, sys.stdout))
        t_err = threading.Thread(target=stream, args=(proc.stderr, stderr_parts, sys.stderr))
        t_out.start()
        t_err.start()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        t_out.join()
        t_err.join()

        return subprocess.CompletedProcess(
            cmd, proc.returncode,
            stdout=b"".join(stdout_parts),
            stderr=b"".join(stderr_parts),
        )

    def adb(self, *args, timeout=30):
        result = subprocess.run(
            [self.adb_path] + list(args), capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()

    def adb_shell(self, *args):
        return self.adb("shell", *args)

    def wait_for_boot(self, timeout=120, background_proc=None):
        """等待设备启动完成，返回 (成功, 耗时秒数)。"""
        subprocess.run([self.adb_path, "wait-for-device"], timeout=60)
        start = time.time()
        while time.time() - start < timeout:
            if background_proc is not None and background_proc.poll() is not None:
                return False, int(time.time() - start)
            result = self.adb_shell("getprop", "sys.boot_completed")
            if result.strip() == "1":
                return True, int(time.time() - start)
            time.sleep(3)
        return False, int(time.time() - start)

    def tap(self, display_id, x, y):
        self.adb_shell("input", "-d", str(display_id), "tap", str(x), str(y))

    def keyevent(self, display_id, code):
        self.adb_shell("input", "-d", str(display_id), "keyevent", str(code))


# 模块级单例，通过 init() 设置
_runner: "AdbRunner | None" = None


def init(adb_path: str) -> None:
    """初始化 AdbRunner。必须在调用 adb 函数前执行。"""
    global _runner
    _runner = AdbRunner(adb_path)


def _ensure_runner() -> AdbRunner:
    if _runner is None:
        raise RuntimeError(
            "adb_utils not initialized. Call adb_utils.init(cfg.ADB) first."
        )
    return _runner


# 模块级便捷函数（委托给 _runner）

def run(cmd, timeout=None, shell=False):
    return _ensure_runner().run(cmd, timeout=timeout, shell=shell)


def run_live(cmd, timeout=None):
    return _ensure_runner().run_live(cmd, timeout=timeout)


def adb(*args, timeout=30):
    return _ensure_runner().adb(*args, timeout=timeout)


def adb_shell(*args):
    return _ensure_runner().adb_shell(*args)


def wait_for_boot(timeout=120, background_proc=None):
    return _ensure_runner().wait_for_boot(timeout=timeout, background_proc=background_proc)


def tap(display_id, x, y):
    return _ensure_runner().tap(display_id, x, y)


def keyevent(display_id, code):
    return _ensure_runner().keyevent(display_id, code)
