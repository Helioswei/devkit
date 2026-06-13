#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../../lib/install_utils.sh"

# ─── Module globals ──────────────────────────────────────────────────────────
HOME_DIR="$HOME"
VIMRC_SRC="$SCRIPT_DIR/.vimrc"
VIMRC_DST="$HOME_DIR/.vimrc"
VIMRC_BAK="$HOME_DIR/.vimrc.bak"
PLUG_DST="$HOME_DIR/.vim/autoload/plug.vim"
PLUG_URL="https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim"
PLUG_MIRROR="https://gitee.com/mirrors/vim-plug/raw/master/plug.vim"

# ─── Pre-flight: check if already fully installed ────────────────────────────────
is_already_installed() {
    # .vimrc MD5 matches source
    if [ ! -f "$VIMRC_DST" ]; then return 1; fi
    local src_md5 dst_md5
    src_md5="$(md5 -q "$VIMRC_SRC" 2>/dev/null || md5sum "$VIMRC_SRC" | cut -d' ' -f1)"
    dst_md5="$(md5 -q "$VIMRC_DST" 2>/dev/null || md5sum "$VIMRC_DST" | cut -d' ' -f1)"
    [ "$src_md5" != "$dst_md5" ] && return 1

    # vim-plug exists
    [ ! -f "$PLUG_DST" ] && return 1

    # plugins installed (plugged dir has content)
    local plugged_dir="$HOME_DIR/.vim/plugged"
    [ ! -d "$plugged_dir" ] && return 1
    [ -z "$(ls -A "$plugged_dir" 2>/dev/null)" ] && return 1

    return 0
}

# ─── Rollback ─────────────────────────────────────────────────────────────────
_rollback_done=0
rollback() {
    [ "$_rollback_done" -eq 1 ] && return
    _rollback_done=1
    if [ -f "$VIMRC_BAK" ] && [ -f "$VIMRC_DST" ]; then
        warn "Restoring previous .vimrc from backup"
        cp -f "$VIMRC_BAK" "$VIMRC_DST"
    fi
}
trap rollback EXIT

# ─── Install vim-plug ─────────────────────────────────────────────────────────
install_plug() {
    if [ -f "$PLUG_DST" ]; then
        ok "vim-plug already installed ($PLUG_DST)"
        return
    fi

    info "Installing vim-plug..."
    mkdir -p "$(dirname "$PLUG_DST")"

    if download_with_retry "$PLUG_URL" "$PLUG_DST" 3 5; then
        ok "vim-plug installed from GitHub"
        return
    fi

    warn "GitHub unreachable, trying mirror..."
    if download_with_retry "$PLUG_MIRROR" "$PLUG_DST" 3 5; then
        ok "vim-plug installed from Gitee mirror"
        return
    fi

    rm -f "$PLUG_DST"
    die "Failed to download vim-plug from all sources"
}

# ─── Backup & Copy vimrc ─────────────────────────────────────────────────────
install_vimrc() {
    if [ ! -f "$VIMRC_SRC" ]; then
        die ".vimrc not found in script directory ($VIMRC_SRC)"
    fi

    local src_md5
    src_md5="$(md5 -q "$VIMRC_SRC" 2>/dev/null || md5sum "$VIMRC_SRC" | cut -d' ' -f1)"

    if [ -f "$VIMRC_DST" ]; then
        local dst_md5
        dst_md5="$(md5 -q "$VIMRC_DST" 2>/dev/null || md5sum "$VIMRC_DST" | cut -d' ' -f1)"

        if [ "$src_md5" = "$dst_md5" ]; then
            ok ".vimrc already installed and unchanged ($VIMRC_DST)"
            return 0
        fi

        # .vimrc 存在但内容不同 — 用户可能修改过
        warn ".vimrc exists but content differs (you may have custom modifications)"
        echo ""
        echo "  Source MD5:  $src_md5 ($VIMRC_SRC)"
        echo "  Current MD5: $dst_md5 ($VIMRC_DST)"
        echo ""
        echo "  Options:"
        echo "    1) Replace  — overwrite with new version (backup saved to .vimrc.bak)"
        echo "    2) Skip     — keep your current .vimrc unchanged"
        echo "    3) Diff     — show differences before deciding"
        echo ""
        read -rp "  Choose (1/2/3): " choice
        case "$choice" in
            1)
                if [ -f "$VIMRC_BAK" ]; then
                    local ts_bak="${VIMRC_BAK}.$(date +%Y%m%d%H%M%S)"
                    info "Backup already exists, saving additional copy to $(basename "$ts_bak")"
                    cp -f "$VIMRC_DST" "$ts_bak"
                else
                    info "Backing up existing .vimrc to .vimrc.bak"
                    cp -f "$VIMRC_DST" "$VIMRC_BAK"
                fi
                cp -f "$VIMRC_SRC" "$VIMRC_DST"
                ok ".vimrc replaced ($VIMRC_DST)"
                ;;
            2)
                ok ".vimrc kept unchanged (skipped)"
                ;;
            3)
                diff --color=always "$VIMRC_DST" "$VIMRC_SRC" 2>/dev/null || diff "$VIMRC_DST" "$VIMRC_SRC"
                echo ""
                read -rp "  Replace? [y/N] " ans
                case "$ans" in
                    [yY]|[yY][eE][sS])
                        cp -f "$VIMRC_DST" "$VIMRC_BAK"
                        cp -f "$VIMRC_SRC" "$VIMRC_DST"
                        ok ".vimrc replaced after review"
                        ;;
                    *)
                        ok ".vimrc kept unchanged (skipped)"
                        ;;
                esac
                ;;
            *)
                ok ".vimrc kept unchanged (skipped)"
                ;;
        esac
        return 0
    fi

    # .vimrc 不存在，直接安装
    cp -f "$VIMRC_SRC" "$VIMRC_DST"
    ok ".vimrc installed to $VIMRC_DST"
}

# ─── Install Plugins ─────────────────────────────────────────────────────────
install_plugins() {
    if ! has_command vim; then
        die "vim not found — please install vim first"
    fi

    info "Running :PlugInstall to install plugins..."
    vim -es -u "$VIMRC_DST" -c "PlugInstall --sync" -c "qa!" 2>&1 || true

    local plugged_dir="$HOME_DIR/.vim/plugged"
    if [ -d "$plugged_dir" ] && [ "$(ls -A "$plugged_dir" 2>/dev/null)" ]; then
        local count
        count=$(find "$plugged_dir" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
        ok "Installed $count plugins in $plugged_dir"
    else
        warn "No plugins installed — you may need to run :PlugInstall manually in vim"
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
    echo "====================================="
    echo "  Vim Configuration Installer"
    echo "====================================="
    echo ""

    if is_already_installed; then
        ok "Vim configuration already fully installed — nothing to do."
        echo ""
        echo "  Config:    $VIMRC_DST"
        echo "  Plugins:   $HOME_DIR/.vim/plugged/"
        echo ""
        echo "  Reinstall plugins: :PlugInstall"
        echo "  Update plugins:    :PlugUpdate"
        _rollback_done=1
        trap - EXIT
        exit 0
    fi

    confirm "This script will:
  1. Install your vim configuration (~/.vimrc)
  2. Install vim-plug (plugin manager)
  3. Install system dependencies (clang, ctags, astyle)
  4. Run :PlugInstall to download vim plugins"

    local os
    os="$(detect_os)"
    info "Detected OS: $os"
    case "$os" in
        macos|debian|rhel) ;;
        *) warn "Unknown OS, will skip system dependency installation" ;;
    esac

    check_network

    install_vimrc
    install_plug

    info "Installing system dependencies..."
    case "$os" in
        macos)
            if ! has_command clang; then
                info "clang not found. Installing Xcode Command Line Tools..."
                xcode-select --install
            else
                ok "clang already available (Xcode CLT)"
            fi
            pkg_install "$os" astyle
            ;;
        debian|rhel)
            pkg_install "$os" clang universal-ctags astyle
            ;;
        *)
            warn "Unsupported OS ($os), skipping system dependency installation"
            ;;
    esac

    install_plugins

    echo ""
    ok "Installation complete!"
    echo ""
    echo "  Config:    $VIMRC_DST"
    echo "  Plugins:   $HOME_DIR/.vim/plugged/"
    echo ""
    echo "  Reinstall plugins: :PlugInstall"
    echo "  Update plugins:    :PlugUpdate"

    _rollback_done=1
    trap - EXIT
}

main "$@"
