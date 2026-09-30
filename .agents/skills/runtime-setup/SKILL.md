---
name: runtime-setup
description: Manage runtime setup actions (Node, Go, Java, Hugo, Gradle) and package mirror integrations.
vendor_neutral: true
version: 1.0.0
triggers:
  - "setup node"
  - "setup go"
  - "setup java"
  - "setup gradle"
  - "pkg cache"
inputs:
  runtime:
    type: string
    description: "Target runtime language (node, go, java, gradle, hugo)"
  version:
    type: string
    description: "Major or specific version string"
---

# Runtime Setup Skill

This vendor-neutral skill defines standard patterns for language runtime installer actions that support self-hosted runners and offline/mirrored package caches.
`setup-cache` is the single setup action for mirror detection and system
repository configuration. It derives a cache from `github.server_url`, honors
an existing `PKG_CACHE` environment value, normalizes it, and exports it
through `GITHUB_ENV`.

## Design Patterns

1. **Architecture Detection**:
   - Standardize CPU architecture naming:
     ```bash
     ARCH=$(uname -m)
     if [ "$ARCH" = "x86_64" ]; then ARCH="x64"; fi
     if [ "$ARCH" = "aarch64" ]; then ARCH="arm64"; fi
     ```

2. **Package Cache Mirror Resolution**:
   - Read the inherited `PKG_CACHE` environment variable.
   - Prepend `https://` if protocol is missing.
   - Strip trailing slashes.
   - Fall back to primary upstream endpoints when `PKG_CACHE` is empty.

3. **PATH & Environment Exports**:
   - Append binary directories to runner PATH:
     ```bash
     echo "$HOME/.runtime/bin" >> "$GITHUB_PATH"
     echo "PATH=$HOME/.runtime/bin:$PATH" >> "$GITHUB_ENV"
     ```

4. **Runtime Config**:
   - For Node: configure npm registry `npm config set registry "$NPM_REGISTRY"` and create `.npmrc`.
   - For Gradle: set Gradle distribution mirror or cache directory.
   - For Maven: set settings.xml repository mirror.

## Action Reference
- `setup-node`: Node.js version resolution & npm pkg-cache.
- `setup-go`: Go SDK downloader.
- `setup-java`: OpenJDK distribution setup.
- `setup-gradle`: Gradle wrapper & mirror installer.
- `setup-hugo`: Hugo Extended binary setup.
- `setup-cache`: Detects and configures the package cache, then exports `PKG_CACHE`.
- `utils/detect-pkg-cache`: Legacy compatibility utility that only computes a hostname; it does not configure repositories or export `PKG_CACHE`.
