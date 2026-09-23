#!/usr/bin/env bash

set -euo pipefail

PKG_CACHE="${PKG_CACHE:-}"
VERSION="${REVIEWDOG_VERSION:-latest}"

# ============================================================
# Normalize pkg-cache
# ============================================================

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

# ============================================================
# Resolve latest
# ============================================================

if [ "$VERSION" = "latest" ]; then

    echo "Resolving latest reviewdog version..."

    if [ -n "$PKG_CACHE" ]; then

        # The pkg-cache is expected to provide the same
        # /releases/latest endpoint as the upstream mirror.
        VERSION="$(
            curl \
                --fail \
                --silent \
                --show-error \
                --location \
                -o /dev/null \
                -w '%{url_effective}' \
                "${BASE_URL}/releases/latest" |
            grep -oE '/tag/v[0-9]+\.[0-9]+\.[0-9]+$' |
            sed 's#.*/tag/v##'
        )

    else

        VERSION="$(
            curl \
                --fail \
                --silent \
                --show-error \
                --location \
                https://api.github.com/repos/reviewdog/reviewdog/releases/latest |
            grep -oE '"tag_name"[[:space:]]*:[[:space:]]*"v[0-9]+\.[0-9]+\.[0-9]+"' |
            head -n 1 |
            sed -E 's/.*"v([0-9]+\.[0-9]+\.[0-9]+)".*/\1/'
        )

    fi

    if [ -z "$VERSION" ]; then
        echo "ERROR: Failed to resolve latest reviewdog version"
        exit 1
    fi

    echo "Resolved version: $VERSION"

else

    # Remove optional v prefix.
    VERSION="${VERSION#v}"

    echo "Using requested reviewdog version: $VERSION"

fi

# ============================================================
# Validate version
# ============================================================

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: Invalid reviewdog version: $VERSION"
    echo "Expected: latest, 0.21.2, or v0.21.2"
    exit 1
fi

# ============================================================
# Platform
# ============================================================

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

# ============================================================
# Download
# ============================================================

ARCHIVE="reviewdog_${VERSION}_${OS}_${ARCH}.tar.gz"

DOWNLOAD_URL="${BASE_URL}/releases/download/v${VERSION}/${ARCHIVE}"

echo
echo "Reviewdog version : $VERSION"
echo "Platform          : $OS/$ARCH"
echo "Download URL      : $DOWNLOAD_URL"
echo

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

# ============================================================
# Extract
# ============================================================

tar \
    -xzf "$TMP_ARCHIVE" \
    -C "$INSTALL_DIR"

chmod +x "$INSTALL_DIR/reviewdog"

echo "$INSTALL_DIR" >> "$GITHUB_PATH"

echo
echo "Reviewdog installed at:"
echo "$INSTALL_DIR/reviewdog"
echo

"$INSTALL_DIR/reviewdog" -version