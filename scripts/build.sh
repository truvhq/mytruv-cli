#!/bin/sh
set -e

BINARY_NAME="mytruv"

detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "darwin" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        *)             echo "unknown" ;;
    esac
}

OS=$(detect_os)
ARCH=$(detect_arch)

if [ "$OS" = "unknown" ] || [ "$ARCH" = "unknown" ]; then
    echo "Error: unsupported platform: $(uname -s) $(uname -m)" >&2
    exit 1
fi

OUTPUT_NAME="${BINARY_NAME}-${OS}-${ARCH}"

echo "Building ${OUTPUT_NAME}..."
echo "  OS:   ${OS}"
echo "  Arch: ${ARCH}"

uv run python -m nuitka \
    --standalone \
    --onefile \
    --output-filename="${OUTPUT_NAME}" \
    --output-dir=dist \
    --include-package=mytruv_cli \
    --python-flag=no_site \
    --assume-yes-for-downloads \
    src/mytruv_cli/main.py

echo ""
echo "Build complete: dist/${OUTPUT_NAME}"

echo "Running smoke test..."
help_output=$("./dist/${OUTPUT_NAME}" --help 2>&1) || {
    echo "Smoke test failed: binary exited non-zero" >&2
    exit 1
}
case "$help_output" in
    *Usage:*) echo "Smoke test passed." ;;
    *) echo "Smoke test failed: --help output missing 'Usage:'" >&2
       echo "Got: $help_output" >&2
       exit 1 ;;
esac
