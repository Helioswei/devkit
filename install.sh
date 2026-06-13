#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/install_utils.sh"

# ─── Register unified devkit alias ────────────────────────────────────────
chmod +x "$SCRIPT_DIR/devkit"
install_alias devkit "$SCRIPT_DIR/devkit"

# ─── Auto-discover modules ──────────────────────────────────────────────────

MODULES_DIR="$SCRIPT_DIR/modules"
MODULE_DESC=()
MODULE_INSTALL=()
MODULE_TYPE=()

for yml in "$MODULES_DIR"/*/module.yml; do
    [ -f "$yml" ] || continue
    mod_dir="$(dirname "$yml")"
    mod_desc="$(grep '^description:' "$yml" | sed 's/description: *//' | tr -d '"')"
    mod_install="$(grep '^install:' "$yml" | sed 's/install: *//' | tr -d '"')"
    mod_type="$(grep '^type:' "$yml" | sed 's/type: *//' | tr -d '"')"
    MODULE_DESC+=("$mod_desc")
    MODULE_INSTALL+=("$mod_dir/$mod_install")
    MODULE_TYPE+=("$mod_type")
done

if [ ${#MODULE_DESC[@]} -eq 0 ]; then
    die "No modules found in $MODULES_DIR"
fi

TOTAL=${#MODULE_DESC[@]}
SELECTED=()
for i in $(seq 0 $((TOTAL - 1))); do SELECTED+=("0"); done
FOCUS=0

# ─── Color codes ────────────────────────────────────────────────────────────
R="\033[0m"
RV="\033[7m"

# ─── Key reader (macOS bash 3.2 兼容) ───────────────────────────────────────
# 返回: up / down / space / enter / a / n / q / other
read_key() {
    local k s1 s2 seq
    # 临时允许 read 超时失败不退出
    set +e
    IFS= read -rsn1 k
    if [[ "$k" == "" ]]; then
        KEY="enter"
        set -e
        return
    fi
    if [[ "$k" == " " ]]; then
        KEY="space"
        set -e
        return
    fi
    if [[ "$k" == "a" || "$k" == "n" || "$k" == "q" ]]; then
        KEY="$k"
        set -e
        return
    fi
    # ESC 序列: 方向键发送 \x1b [ A 或 \x1b [ B
    if [[ "$k" == $'\x1b' ]]; then
        IFS= read -rsn1 -t1 s1
        IFS= read -rsn1 -t1 s2
        seq="${s1}${s2}"
        if [[ "$seq" == "[A" ]]; then
            KEY="up"
        elif [[ "$seq" == "[B" ]]; then
            KEY="down"
        elif [[ "$seq" == "[D" ]]; then
            KEY="left"
        elif [[ "$seq" == "[C" ]]; then
            KEY="right"
        else
            KEY="other"
        fi
        set -e
        return
    fi
    KEY="other"
    set -e
}

# ─── Render menu ─────────────────────────────────────────────────────────────

render_menu() {
    printf "\033[2J\033[H"
    echo "  devkit — 统一开发者工具包安装器"
    echo ""
    echo "  ↑↓ 移动焦点   空格 选中/取消   回车 确认安装   a 全选   n 清空   q 退出"
    echo ""
    for i in "${!MODULE_DESC[@]}"; do
        num=$((i + 1))
        type_tag="${MODULE_TYPE[$i]}"
        if [ "${SELECTED[$i]}" = "1" ]; then
            check="[◉]"
        else
            check="[ ]"
        fi
        desc_text="${MODULE_DESC[$i]}  (${type_tag})"
        if [ "$i" -eq "$FOCUS" ]; then
            printf "  %s %s ${RV}%s${R}\n" "$check" "$num" "$desc_text"
        else
            printf "  %s %s %s\n" "$check" "$num" "$desc_text"
        fi
    done
    echo ""
    sel_count=0
    for s in "${SELECTED[@]}"; do [ "$s" = "1" ] && sel_count=$((sel_count + 1)); done
    if [ "$sel_count" -gt 0 ]; then
        printf "  已选中 %d 个模块\n" "$sel_count"
    else
        echo "  未选择任何模块"
    fi
}

# ─── Interactive loop ────────────────────────────────────────────────────────

render_menu

while true; do
    read_key
    case "$KEY" in
        up)
            FOCUS=$((FOCUS - 1))
            [ "$FOCUS" -lt 0 ] && FOCUS=$((TOTAL - 1))
            render_menu
            ;;
        down)
            FOCUS=$((FOCUS + 1))
            [ "$FOCUS" -ge "$TOTAL" ] && FOCUS=0
            render_menu
            ;;
        space)
            if [ "${SELECTED[$FOCUS]}" = "1" ]; then
                SELECTED[$FOCUS]="0"
            else
                SELECTED[$FOCUS]="1"
            fi
            render_menu
            ;;
        a)
            for i in "${!SELECTED[@]}"; do SELECTED[$i]="1"; done
            render_menu
            ;;
        n)
            for i in "${!SELECTED[@]}"; do SELECTED[$i]="0"; done
            render_menu
            ;;
        q)
            printf "\033[2J\033[H"
            echo "  已退出安装器。"
            exit 0
            ;;
        enter)
            break
            ;;
    esac
done

# ─── Collect confirmed selections ───────────────────────────────────────────
printf "\033[2J\033[H"

CONFIRMED=()
for i in "${!SELECTED[@]}"; do
    if [ "${SELECTED[$i]}" = "1" ]; then
        CONFIRMED+=("$i")
    fi
done

if [ ${#CONFIRMED[@]} -eq 0 ]; then
    echo "  未选择任何模块，退出。"
    exit 0
fi

echo "  即将安装:"
for idx in "${CONFIRMED[@]}"; do
    num=$((idx + 1))
    echo "    [$num] ${MODULE_DESC[$idx]}"
done
echo ""

# ─── Run selected module installers ─────────────────────────────────────────

SUCCESS=0
FAIL=0

for idx in "${CONFIRMED[@]}"; do
    install_script="${MODULE_INSTALL[$idx]}"
    desc="${MODULE_DESC[$idx]}"

    echo ""
    info "Installing: $desc"

    if bash "$install_script"; then
        ok "$desc installed"
        SUCCESS=$((SUCCESS + 1))
    else
        error "$desc failed (exit code: $?)"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "====================================="
if [ "$FAIL" -eq 0 ]; then
    ok "All $SUCCESS modules installed successfully!"
else
    warn "Results: $SUCCESS succeeded, $FAIL failed"
fi
echo "====================================="
