# devkit shared bash utilities — meant to be sourced, not executed directly

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─── Logging ──────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

die() {
    error "$*"
    echo ""
    exit 1
}

# ─── Command Detection ───────────────────────────────────────────────────────
has_command() { command -v "$1" >/dev/null 2>&1; }

# ─── OS Detection ────────────────────────────────────────────────────────────
detect_os() {
    local kernel
    kernel="$(uname -s)"
    case "$kernel" in
        Darwin)
            echo "macos"
            return
            ;;
        Linux)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                case "$ID" in
                    ubuntu|debian|devuan)  echo "debian"; return ;;
                    centos|rhel|fedora)    echo "rhel";   return ;;
                    *)                     echo "unknown ($ID)" ;;
                esac
            fi
            echo "unknown"
            ;;
        *)
            echo "unknown ($kernel)"
            ;;
    esac
}

# ─── Package Manager ─────────────────────────────────────────────────────────
pkg_install() {
    local os="$1"; shift
    local packages=("$@")

    case "$os" in
        macos)
            if ! has_command brew; then
                die "Homebrew not found. Install it first: https://brew.sh"
            fi
            for pkg in "${packages[@]}"; do
                if brew list "$pkg" >/dev/null 2>&1; then
                    ok "$pkg already installed"
                else
                    info "Installing $pkg via Homebrew..."
                    brew install "$pkg" || die "Failed to install $pkg"
                    ok "$pkg installed"
                fi
            done
            ;;
        debian)
            if ! has_command sudo; then
                die "sudo not found — install it or run as root"
            fi
            info "Updating apt cache..."
            sudo apt-get update -qq || die "apt-get update failed"
            for pkg in "${packages[@]}"; do
                if dpkg -s "$pkg" 2>/dev/null | grep -q 'Status: install ok installed'; then
                    ok "$pkg already installed"
                else
                    info "Installing $pkg via apt-get..."
                    sudo apt-get install -y -qq "$pkg" || die "Failed to install $pkg"
                    ok "$pkg installed"
                fi
            done
            ;;
        rhel)
            local mgr="yum"
            has_command dnf && mgr="dnf"
            if ! has_command sudo; then
                die "sudo not found — install it or run as root"
            fi
            for pkg in "${packages[@]}"; do
                if rpm -q "$pkg" >/dev/null 2>&1; then
                    ok "$pkg already installed"
                else
                    info "Installing $pkg via $mgr..."
                    sudo "$mgr" install -y -q "$pkg" || die "Failed to install $pkg"
                    ok "$pkg installed"
                fi
            done
            ;;
        *)
            die "Unsupported OS: $os — please install packages manually"
            ;;
    esac
}

# ─── Network Check ───────────────────────────────────────────────────────────
check_network() {
    local ping_host="${1:-baidu.com}"
    info "Checking network connectivity ($ping_host)..."
    if ! has_command ping; then
        warn "ping not found, skipping network check"
        return
    fi
    if ! ping -c 2 -W 3 "$ping_host" >/dev/null 2>&1; then
        die "No network connection. Please check your network and retry."
    fi
    ok "Network OK"
}

# ─── Download with Retry ────────────────────────────────────────────────────
download_with_retry() {
    local url="$1" dest="$2"
    local retries="${3:-3}" delay="${4:-5}"
    local attempt=1

    while [ "$attempt" -le "$retries" ]; do
        info "Download attempt $attempt/$retries from $url"

        if has_command curl; then
            if curl -fSL --connect-timeout 10 --max-time 30 \
               -o "$dest" "$url" 2>/dev/null; then
                return 0
            fi
        elif has_command wget; then
            if wget -q --timeout=10 --tries=1 -O "$dest" "$url" 2>/dev/null; then
                return 0
            fi
        else
            die "Neither curl nor wget found"
        fi

        warn "Attempt $attempt failed"
        attempt=$((attempt + 1))
        [ "$attempt" -le "$retries" ] && sleep "$delay"
    done
    return 1
}

# ─── User Confirmation ───────────────────────────────────────────────────────
confirm() {
    local description="$1"
    echo ""
    echo "$description"
    echo ""
    read -rp "Continue? [y/N] " answer
    case "$answer" in
        [yY]|[yY][eE][sS]) return ;;
        *) echo "Aborted."; exit 0 ;;
    esac
}

# ─── Python 3 Check ──────────────────────────────────────────────────────────
require_python3() {
    local min_version="${1:-38}"

    if ! command -v python3 &>/dev/null; then
        die "python3 not found. Install Python 3 first:
  macOS:  brew install python3
  Linux:  sudo apt install python3"
    fi

    local py_version
    py_version=$(python3 -c "import sys; print(sys.version_info.major * 10 + sys.version_info.minor)")
    if [ "$py_version" -lt "$min_version" ]; then
        local py_ver
        py_ver=$(python3 --version)
        die "Python 3.$((min_version / 10)).$((min_version % 10))+ required, found $py_ver"
    fi

    info "Python: $(python3 --version)"
}

# ─── Alias Installation ──────────────────────────────────────────────────────
install_alias() {
    local alias_name="$1"
    local alias_target="$2"
    local alias_line="alias $alias_name='$alias_target'  # devkit"

    # Check if command already accessible
    if command -v "$alias_name" &>/dev/null; then
        ok "$alias_name: already accessible from anywhere"
        return 0
    fi

    # Check if alias already configured in existing file
    local alias_found=false alias_file=""
    local zsh_custom="${ZSH_CUSTOM:-}"
    for f in ~/.aliases "${zsh_custom}/aliases.zsh" ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile; do
        if [ -f "$f" ] && grep -q "alias ${alias_name}=" "$f" 2>/dev/null; then
            alias_found=true
            alias_file="$f"
            break
        fi
    done

    if $alias_found; then
        ok "$alias_name: alias already configured in $alias_file"
        return 0
    fi

    # Select target file (priority order)
    local target_file=""
    local shell_name="$(basename "$SHELL")"

    # Priority 1: ~/.aliases if it exists and is sourced by shell profile
    if [ -f ~/.aliases ]; then
        local rc_file=""
        case "$shell_name" in
            zsh)  rc_file=~/.zshrc ;;
            bash) rc_file=~/.bashrc ;;
            *)    rc_file=~/.profile ;;
        esac
        if [ -f "$rc_file" ] && grep -qE "source\s+~/.aliases|\.\s+~/.aliases" "$rc_file" 2>/dev/null; then
            target_file=~/.aliases
            info "Target: ~/.aliases (already sourced by $rc_file)"
        fi
    fi

    # Priority 2: $ZSH_CUSTOM/aliases.zsh (Oh My Zsh auto-loads)
    local zsh_custom="${ZSH_CUSTOM:-}"
    if [ -z "$target_file" ] && [ "$shell_name" = "zsh" ] && [ -n "$zsh_custom" ] && [ -d "$zsh_custom" ]; then
        target_file="$zsh_custom/aliases.zsh"
        info "Target: $zsh_custom/aliases.zsh (Oh My Zsh auto-loads)"
    fi

    # Priority 3: Create ~/.aliases and add source line
    if [ -z "$target_file" ]; then
        local rc_file=""
        case "$shell_name" in
            zsh)  rc_file=~/.zshrc ;;
            bash) rc_file=~/.bashrc ;;
            *)    rc_file=~/.profile ;;
        esac
        touch ~/.aliases
        target_file=~/.aliases
        if [ -f "$rc_file" ] && ! grep -qE "source\s+~/.aliases|\.\s+~/.aliases" "$rc_file" 2>/dev/null; then
            echo "" >> "$rc_file"
            echo "source ~/.aliases  # custom aliases" >> "$rc_file"
            info "Added 'source ~/.aliases' to $rc_file"
        fi
        info "Target: ~/.aliases (created)"
    fi

    # Write alias
    echo "" >> "$target_file"
    echo "$alias_line" >> "$target_file"
    ok "Added: $alias_line"
    info "Run 'source $target_file' or restart terminal to activate."
}
