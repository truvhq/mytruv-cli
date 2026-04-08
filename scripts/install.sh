#!/bin/sh
set -e

REPO="truvhq/mytruv-cli"
BINARY_NAME="mytruv"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

main() {
    os=$(detect_os)
    arch=$(detect_arch)

    if [ -z "$os" ] || [ -z "$arch" ]; then
        echo "Error: unsupported platform: $(uname -s) $(uname -m)" >&2
        exit 1
    fi

    version="${MYTRUV_VERSION:-}"
    if [ -z "$version" ]; then
        version=$(get_latest_version)
    fi
    if [ -z "$version" ]; then
        echo "Error: could not determine latest version." >&2
        echo "Set MYTRUV_VERSION=vX.Y.Z or GITHUB_TOKEN to work around GitHub API rate limits." >&2
        exit 1
    fi

    case "$version" in
        v[0-9]*) ;;
        *) echo "Error: unexpected version format: '${version}'" >&2; exit 1 ;;
    esac

    asset="${BINARY_NAME}-${os}-${arch}.tar.gz"
    url="https://github.com/${REPO}/releases/download/${version}/${asset}"
    checksum_url="${url}.sha256"

    tmpdir=$(mktemp -d)
    trap 'rm -rf "$tmpdir"' EXIT

    echo "Downloading ${BINARY_NAME} ${version} for ${os}/${arch}..."
    curl --retry 3 --retry-delay 2 --max-time 300 --connect-timeout 30 -fsSL "$url" -o "${tmpdir}/${asset}"
    curl --retry 3 --retry-delay 2 --max-time 60 --connect-timeout 30 -fsSL "$checksum_url" -o "${tmpdir}/${asset}.sha256"

    echo "Verifying checksum..."
    verify_checksum "${tmpdir}" "${asset}"

    echo "Extracting..."
    extracted="${BINARY_NAME}-${os}-${arch}"
    tar -xzf "${tmpdir}/${asset}" -C "${tmpdir}" "${extracted}"

    echo "Installing to ${INSTALL_DIR}..."
    if [ -w "$INSTALL_DIR" ]; then
        mv "${tmpdir}/${extracted}" "${INSTALL_DIR}/${BINARY_NAME}"
        chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
    else
        sudo mv "${tmpdir}/${extracted}" "${INSTALL_DIR}/${BINARY_NAME}"
        sudo chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
    fi

    echo ""
    echo "${BINARY_NAME} ${version} installed successfully!"
    echo "Run '${BINARY_NAME} --help' to get started."
}

detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "darwin" ;;
        Linux*)  echo "linux" ;;
        *)       echo "" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        *)             echo "" ;;
    esac
}

get_latest_version() {
    auth_header=""
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        auth_header="-H \"Authorization: Bearer ${GITHUB_TOKEN}\""
    fi
    eval curl --retry 3 --retry-delay 2 --max-time 30 --connect-timeout 10 -fsSL \
        "$auth_header" \
        "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name"' \
        | head -1 \
        | sed 's/.*"tag_name": *"//;s/".*//'
}

verify_checksum() {
    dir="$1"
    file="$2"

    expected=$(awk '{print $1}' "${dir}/${file}.sha256")

    if [ -z "$expected" ]; then
        echo "Error: checksum file is empty or malformed" >&2
        exit 1
    fi

    if command -v sha256sum >/dev/null 2>&1; then
        actual=$(sha256sum "${dir}/${file}" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        actual=$(shasum -a 256 "${dir}/${file}" | awk '{print $1}')
    else
        echo "Error: no sha256 tool found, cannot verify download" >&2
        exit 1
    fi

    if [ "$expected" != "$actual" ]; then
        echo "Error: checksum mismatch" >&2
        echo "  expected: ${expected}" >&2
        echo "  actual:   ${actual}" >&2
        exit 1
    fi
}

main
