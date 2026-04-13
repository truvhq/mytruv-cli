#!/bin/sh
# mytruv CLI installer — installs mytruv via uv
# Usage: curl -fsSL https://raw.githubusercontent.com/truvhq/mytruv-cli/master/install.sh | sh
#
# Environment variables:
#   MYTRUV_VERSION  - Pin to a specific git ref (tag, branch, commit). Default: master
#   NO_COLOR        - Disable colored output
set -eu

# ── Helpers ──────────────────────────────────────────────────

BOLD=""
GREEN=""
RED=""
RESET=""
if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then
    BOLD="\033[1m"
    GREEN="\033[32m"
    RED="\033[31m"
    RESET="\033[0m"
fi

info() { printf "${GREEN}info${RESET}  %s\n" "$1"; }
warn() { printf "${RED}error${RESET} %s\n" "$1" >&2; }
die()  { warn "$1"; exit 1; }

need() {
    command -v "$1" >/dev/null 2>&1
}

# ── Parse flags ──────────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --help|-h)
            cat <<'EOF'
mytruv CLI installer

Installs the `mytruv` CLI globally using uv. Installs uv first if needed.

Usage:
    curl -fsSL https://raw.githubusercontent.com/truvhq/mytruv-cli/master/install.sh | sh

Environment variables:
    MYTRUV_VERSION      Pin a git ref (tag, branch, or commit). Default: master
    NO_COLOR            Disable colored output

After install:
    mytruv auth login   Authenticate with MyTruv
    mytruv --help       See all commands
EOF
            exit 0
            ;;
    esac
done

# ── Configuration ────────────────────────────────────────────

REPO_URL="https://github.com/truvhq/mytruv-cli.git"
VERSION="${MYTRUV_VERSION:-master}"
PACKAGE_SPEC="git+${REPO_URL}@${VERSION}"

# ── Install uv if missing ────────────────────────────────────

if ! need uv; then
    info "uv not found. Installing uv..."
    need curl || die "curl is required but not found. Install it first."
    curl -LsSf https://astral.sh/uv/install.sh | sh || die "uv install failed."

    # uv's installer drops the binary in ~/.local/bin (or ~/.cargo/bin as fallback).
    # Make it available to this shell without requiring a restart.
    for candidate in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -x "$candidate/uv" ]; then
            PATH="$candidate:$PATH"
            export PATH
            break
        fi
    done

    need uv || die "uv was installed but is not on PATH. Restart your shell and re-run this script."
fi

# ── Install mytruv ──────────────────────────────────────────

info "Installing mytruv CLI (${VERSION})..."

# --force lets users re-run the installer to upgrade.
uv tool install --force "$PACKAGE_SPEC" || die "Failed to install mytruv."

info "mytruv installed"

# ── PATH check ──────────────────────────────────────────────

UV_BIN_DIR="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"

case ":${PATH}:" in
    *":${UV_BIN_DIR}:"*)
        ;;
    *)
        printf "\n"
        printf "  ${BOLD}Add %s to your PATH:${RESET}\n" "$UV_BIN_DIR"
        printf "    export PATH=\"%s:\$PATH\"\n" "$UV_BIN_DIR"
        printf "\n"
        printf "  Or run: uv tool update-shell\n"
        ;;
esac

# ── Next steps ─────────────────────────────────────────────

printf "\n"
printf "  %bGet started:%b\n" "$BOLD" "$RESET"
printf "    mytruv auth login            # Authenticate with MyTruv\n"
printf "    mytruv --help                # See all commands\n"
printf "\n"
printf "  %bDocs:%b https://github.com/truvhq/mytruv-cli\n" "$BOLD" "$RESET"
printf "\n"
