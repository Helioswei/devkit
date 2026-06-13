"""Grep patterns for log subsystems.

Each entry maps a subsystem name to a list of grep patterns.
Patterns are combined with `|` (OR) for grep -E.
"""

# Patterns for "parse" mode (keep matching lines)
PARSE = {
    # ─── Android 系统核心 ──────────────────────────────────────────────────────
    "activity": [
        r"ActivityManager",
        r"ActivityThread",
        r"am_.*_proc",
        r"Force finishing activity",
        r"Process died",
        r"Low Memory Killer",
        r"ANR in ",
        r"ActivityRecord",
    ],
    "package": [
        r"PackageManager",
        r"PackageManagerService",
        r"PackageParser",
        r"dex2oat",
        r"ART:.*oat",
    ],
    "crash": [
        r"F DEBUG",
        r"Fatal Exception",
        r"ANDROID_RUNTIME",
        r"backtrace:",
        r"Build fingerprint:",
        r"pid: .*tid: .*>>>.*<<<",
        r"signal ",
    ],
    "boot": [
        r"SystemServerTiming",
        r"Boot completed",
        r"system_server.*ready",
        r"init.*Starting",
        r"Zygote.*started",
        r"SystemServiceManager.*Starting",
    ],
    "input": [
        r"dispatchKeyEvent",
        r"dispatchPointerEvent",
        r"InputReader",
        r"InputDispatcher",
        r"InputTransport",
        r"InterceptingKey",
    ],
    "ime": [
        r"InputMethodManagerService",
        r"InputMethodService",
        r"show_input_panel_surface",
        r"hide_input_panel_surface",
        r"bridge_shell_request_inputpanel_visibility",
        r"handle_update_inputmethod_transform",
    ],

    # ─── 窗窗管理（Android WMS）───────────────────────────────────────────────
    "wms": [
        r"WindowManagerService",
        r"setWindowVisibilityLocked",
        r"handleAnimationDone",
        r"finishDrawWindow",
        r"loadWindowAnimation",
        r"finishExit",
        r"addWindow windowId",
        r"updateWindowInfoLocked",
    ],
    "display": [
        r"DisplayManagerService",
        r"LogicalDisplay",
        r"DisplayDevice",
        r"DisplayPolicy",
        r"viewport",
        r"overscan",
    ],
    "gfx": [
        r"SurfaceFlinger",
        r"BufferQueue",
        r"GraphicBuffer",
        r"EGL_",
        r"GL_",
        r"RenderThread",
        r"flushLayerUpdates",
    ],

    # ─── 网络/连接 ─────────────────────────────────────────────────────────────
    "network": [
        r"ConnectivityService",
        r"NetworkMonitor",
        r"WifiService",
        r"wifi.*connected",
        r"wifi.*disconnected",
        r"DnsResolver",
    ],
    "bluetooth": [
        r"BluetoothAdapter",
        r"BluetoothDevice",
        r"BluetoothGatt",
        r"A2dp.*state",
    ],
}

# Patterns for "delete" mode (remove matching lines)
DELETE = {
    "noisy": [
        r"ConnectivityService",
    ],
    "chatty": [
        r"\/usr\/lib64\/",
    ],
}
