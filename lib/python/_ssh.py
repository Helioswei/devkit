from __future__ import annotations

"""SSH/SCP command construction helpers.

Provides unified command building for SSH and SCP operations,
with automatic port flag handling based on host format:
  - SSH config alias (short name, no @ and no dots): port from ~/.ssh/config
  - user@host: add -p/-P when port != 22
  - bare IP/hostname (has dots, no @): add -p/-P when port != 22
"""


def is_alias(host: str) -> bool:
    """True if host is an SSH config alias (short name, no @ and no dots).

    "dev" → alias (port from ~/.ssh/config)
    "192.168.1.100" → NOT alias (bare IP, needs port flag)
    "build@192.168.1.100" → NOT alias (user@host)
    "server.example.com" → NOT alias (FQDN, needs port flag)
    """
    if "@" in host:
        return False
    return "." not in host


def ssh_cmd(host: str, command: str, port: int | None = None) -> list[str]:
    """Build SSH command list.

    For SSH config aliases, port comes from ~/.ssh/config (no -p flag).
    For user@host addresses, -p flag is added if port != 22.
    """
    cmd = ["ssh"]
    if not is_alias(host) and port and port != 22:
        cmd += ["-p", str(port)]
    cmd += [host, command]
    return cmd


def scp_upload_cmd(
    local: str, host: str, remote: str,
    port: int | None = None, recursive: bool = False
) -> list[str]:
    """Build SCP upload command list.

    For SSH config aliases, port comes from ~/.ssh/config (no -P flag).
    For user@host addresses, -P flag is added if port != 22.
    """
    cmd = ["scp"]
    if not is_alias(host) and port and port != 22:
        cmd += ["-P", str(port)]
    if recursive:
        cmd += ["-r"]
    cmd += [local, f"{host}:{remote}"]
    return cmd


def scp_download_cmd(
    host: str, remote: str, local: str,
    port: int | None = None, recursive: bool = True
) -> list[str]:
    """Build SCP download command list."""
    cmd = ["scp"]
    if not is_alias(host) and port and port != 22:
        cmd += ["-P", str(port)]
    if recursive:
        cmd += ["-r"]
    cmd += [f"{host}:{remote}", local]
    return cmd
