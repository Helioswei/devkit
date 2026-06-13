#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEVKIT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../../lib/install_utils.sh"

require_python3
install_alias devkit "$DEVKIT_ROOT/devkit"
ok "net module installed. Run 'devkit net scan' or 'devkit net up <file>'."
