#!/usr/bin/env bash

set -euo pipefail

PKG_CACHE="${PKG_CACHE:-}"
VERSION="${REVIEWDOG_VERSION:-latest}"

# ------------------------------------------------------------
# Normalize package cache
# ------------------------------------------------------------

if [ -n "$PKG_CACHE" ]; then

    case "$PKG_CACHE" in
        http://*|https://*)
            ;;
        *)
            PKG_CACHE="https://${PKG_CACHE}"
            ;;
    esac

    PKG_CACHE="${PKG_CACHE%/}"

    BASE_URL="${PKG_CACHE}/github.com/reviewdog/reviewdog"

    echo "Using pkg-cache mirror:"
    echo "$BASE_URL"

else

    BASE_URL="https://github.com/reviewdog/reviewdog"

    echo "Using official reviewdog releases:"
    echo "$BASE_URL"

fi

# ------------------------------------------------------------
# Resolve version
# ------------------------------------------------------------

if [ "$VERSION" = "latest" ]; then

    echo "Resolving latest reviewdog version..."

    if [ -n "$PKG_CACHE" ]; then

        VERSION="$(
            curl \
                --fail \
                --silent \
                --show-error \
                -L \
                "${BASE_URL}/releases/latest" |
            grep -oP 'v[0-9]+\.[0-9]+\.[0-9]+' |
            head -n 1 |
            sed 's/^v//'
        )

    else

        VERSION="$(
            curl \
                --fail \
                --silent \
                --show-error \
                https://api.github.com/repos/reviewdog/reviewdog/releases/latest |
            grep -oP '"tag_name"\s*:\s*"\K[^"]+' |
            head -n 1 |
            sed 's/^v//'
        )

    fi

fi

VERSION="${VERSION#v}"

if [ -z "$VERSION" ]; then
    echo "ERROR: Could not determine reviewdog version"
    exit 1
fi

# ------------------------------------------------------------
# Detect platform
# ------------------------------------------------------------

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux)
        ;;
    Darwin)
        ;;
    *)
        echo "Unsupported operating system: $OS"
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64|amd64)
        ARCH="x86_64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    armv7l)
        ARCH="armv7"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

ARCHIVE="reviewdog_${VERSION}_${OS}_${ARCH}.tar.gz"

DOWNLOAD_URL="${BASE_URL}/releases/download/v${VERSION}/${ARCHIVE}"

echo "Reviewdog version : $VERSION"
echo "Platform          : $OS/$ARCH"
echo "Download URL      : $DOWNLOAD_URL"

# ------------------------------------------------------------
# Install
# ------------------------------------------------------------

INSTALL_DIR="${RUNNER_TEMP:-/tmp}/reviewdog-bin"

mkdir -p "$INSTALL_DIR"

TMP_ARCHIVE="${RUNNER_TEMP:-/tmp}/${ARCHIVE}"

curl \
    --fail \
    --location \
    --retry 5 \
    --retry-delay 5 \
    --retry-all-errors \
    --output "$TMP_ARCHIVE" \
    "$DOWNLOAD_URL"

tar \
    -xzf "$TMP_ARCHIVE" \
    -C "$INSTALL_DIR"

chmod +x "$INSTALL_DIR/reviewdog"

echo "$INSTALL_DIR" >> "$GITHUB_PATH"

echo
echo "Reviewdog installed:"
echo "$INSTALL_DIR/reviewdog"

"$INSTALL_DIR/reviewdog" -version