#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEVKIT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../../lib/install_utils.sh"

require_python3 38
chmod +x "$SCRIPT_DIR/fw"
chmod +x "$DEVKIT_ROOT/devkit"
install_alias devkit "$DEVKIT_ROOT/devkit"
ok "fw module installed. Run 'devkit fw doctor' to check environment."
