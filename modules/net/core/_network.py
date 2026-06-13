#!/usr/bin/env python3
"""LAN subnet scanner — cross-platform."""

import argparse
import os
import platform
import socket
import subprocess
import sys


PREFIX = os.environ.get("DEVKIT_PREFIX", "net")


def _get_local_ip():
    """Get the primary local IP address (cross-platform)."""
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", "en0"],
            capture_output=True, text=True, timeout=5,
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"],
            capture_output=True, text=True, timeout=5,
        )
        for part in result.stdout.split():
            try:
                socket.inet_aton(part)
                return part
            except OSError:
                continue
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def _ping_host(host: str, timeout_sec: int = 1) -> bool:
    """Ping a host and return True if reachable."""
    system = platform.system().lower()
    cmd = ["ping", "-c", "1"]
    if system == "windows":
        cmd = ["ping", "-n", "1"]
        timeout_flag = "-w"
        timeout_val = str(timeout_sec * 1000)
    elif system == "darwin":
        # macOS: -W is waittime in milliseconds, -t is TTL (NOT timeout)
        timeout_flag = "-W"
        timeout_val = str(timeout_sec * 1000)
    else:
        # Linux: -W is timeout in seconds
        timeout_flag = "-W"
        timeout_val = str(timeout_sec)

    cmd += [timeout_flag, timeout_val, host]

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout_sec + 3,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _scan(timeout: int = 1, log_file: str = "upip") -> int:
    """Scan local subnet for reachable hosts."""
    ip = _get_local_ip()
    if not ip:
        print("Error: could not determine local IP address", file=sys.stderr)
        return 1

    parts = ip.split(".")
    subnet = ".".join(parts[:3])
    print(f"Local IP: {ip}")
    print(f"Scanning subnet: {subnet}.0/24")

    reachable = []
    for i in range(1, 255):
        host = f"{subnet}.{i}"
        if _ping_host(host, timeout):
            print(f"  {host} is UP")
            reachable.append(host)
        else:
            print(f"  {host} is down")

    with open(log_file, "w") as f:
        f.write(f"Local IP: {ip}\n")
        f.write(f"Subnet: {subnet}.0/24\n")
        for host in reachable:
            f.write(f"{host} is up\n")

    print(f"\n{len(reachable)} hosts reachable. Results saved to {log_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog=f"{PREFIX} scan", description="自动识别本机 IP，扫描局域网存活主机")
    parser.add_argument("-t", "--timeout", type=int, default=1, help="Ping 超时（秒，默认 1）")
    parser.add_argument("-o", "--output", default="upip", help="结果日志文件（默认 upip）")
    args = parser.parse_args()
    return _scan(timeout=args.timeout, log_file=args.output)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
