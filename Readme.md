# Forgejo CI Actions

A production-ready collection of **reusable composite actions** designed for **Forgejo, Gitea, and GitHub Actions compatible CI/CD pipelines**.

These actions simplify common CI tasks such as:

* ⚙️ Language runtime setup with mirror support
* 🐳 Docker build, multi-platform build, OCI export, and push
* 🛡️ Security & vulnerability scanning (Gitleaks + Trivy)
* 🌐 Static site building & deployment
* 📦 Package publishing (Maven & Gradle)
* 🧰 Git operations & package cache integrations

The actions are optimized for **self-hosted runners**, **pkg-cache mirrors**, **air-gapped networks**, and **multi-platform CI environments**.

---

# 📦 Available Actions

## 🏗️ Build & Deployment Actions

### `build-angular`

Build an Angular project.

**Features:**
* Installs dependencies with optional `--force` flag
* Configurable base href and build configurations
* Custom working directory support

```yaml
- uses: actions/forgejo/build-angular@v1
  with:
    working_dir: frontend
    base_href: "/"
    build_configuration: production
    force_install: true
```

---

### `build-hugo`

Build a Hugo static site.

```yaml
- uses: actions/forgejo/build-hugo@v1
  with:
    working_dir: site
    base_url: "/blog/"
```

---

### `deploy-pages`

Deploy static site content to a `gh-pages` branch.

**Features:**
* Cleans orphan deployment branch
* Prevents nested git repositories
* Configurable build output directory

```yaml
- uses: actions/forgejo/deploy-pages@v1
  with:
    site_path: dist
    git_user: CI Bot
    git_email: ci@example.com
```

---

### `clean-sync`

Reinitialize repository history and push clean commits to a target remote.

```yaml
- uses: actions/forgejo/clean-sync@v1
  with:
    remote_url: https://forgejo.example.com/user/target-repo.git
    token: ${{ secrets.SYNC_TOKEN }}
    user_name: "Sync Bot"
    user_email: "sync@example.com"
    branch: main
```

---

## 🐳 Docker & Container Actions

### `setup-docker`

Install Docker daemon (if missing) and configure custom registry mirrors.

```yaml
- uses: actions/forgejo/setup-docker@v1
  with:
    registry_mirror: "https://mirror.gcr.io"
```

---

### `docker-login`

Login to a container registry.

```yaml
- uses: actions/forgejo/docker-login@v1
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

---

### `docker-build`

Build a single-platform Docker image exported directly to a local OCI archive tarball.

```yaml
- uses: actions/forgejo/docker-build@v1
  with:
    registry: registry.example.com
    namespace: dev
    image: my-app
    tag: ${{ github.sha }}
```

---

### `docker-multi-build`

Build multi-architecture Docker images with platform validation and alias support (e.g. `linux/amd64`, `linux/arm64`, `armhf`, `armv7`, `x86_64`, `aarch64`).

**Features:**
* Automatically normalizes platform aliases (e.g. `armhf`/`armv7` to `linux/arm/v7`, `x86_64` to `linux/amd64`, `aarch64` to `linux/arm64`)
* Validates platform buildability before building OCI archive
* Outputs `image` reference and `supported_platforms` list

```yaml
- uses: actions/forgejo/docker-multi-build@v1
  with:
    registry: registry.example.com
    namespace: dev
    image: my-app
    tag: latest
    platforms: "linux/amd64,arm64,armhf"
    validate_platforms: "true"
```

---

### `docker-push`

Push OCI tarball or local Docker images to the destination registry.

```yaml
- uses: actions/forgejo/docker-push@v1
  with:
    registry: registry.example.com
    namespace: dev
    image: my-app
    tag: latest
```

---

### `link-docker-image`

Link container images with repository package registries.

---

## ⚙️ Language Setup & Publishing Actions

### `setup-node`

Install Node.js with optional **pkg-cache mirror** acceleration.

```yaml
- uses: actions/forgejo/setup-node@v1
  with:
    node_version: 20
    pkg_cache: ${{ steps.pkg.outputs.pkg_cache }}
```

---

### `setup-go`

Install Go SDK.

```yaml
- uses: actions/forgejo/setup-go@v1
  with:
    go_version: "1.22"
```

---

### `setup-java`

Install OpenJDK.

```yaml
- uses: actions/forgejo/setup-java@v1
  with:
    java_version: "21"
```

---

### `setup-maven`

Install Apache Maven with automatic version resolution and `pkg-cache` mirror support.

```yaml
- uses: actions/forgejo/setup-maven@v1
  with:
    maven_version: "latest"
    pkg_cache: ${{ steps.pkg.outputs.pkg_cache }}
```

---

### `setup-gradle`

Install Gradle runtime with mirror support.

---

### `setup-hugo`

Install Hugo Extended binary.

---

### `publish-maven`

Publish Java packages using Maven or Gradle scripts.

```yaml
- uses: actions/forgejo/publish-maven@v1
  with:
    registry_url: https://forgejo.example.com/api/packages/user/maven
    token: ${{ secrets.PACKAGE_TOKEN }}
```

---

## 🛡️ Security & Scanning Actions

### `security-scan`

Run comprehensive secret detection (Gitleaks) and dependency vulnerability scans (Trivy).

```yaml
- uses: actions/forgejo/security-scan@v1
  with:
    severity: "HIGH,CRITICAL"
    fail_on_secrets: true
    fail_on_vulnerabilities: true
```

---

### `container-scan`

Scan container image archives for vulnerabilities using Trivy.

```yaml
- uses: actions/forgejo/container-scan@v1
  with:
    image_tar: "my-app.oci.tar"
    severity: "HIGH,CRITICAL"
```

---

### `setup-trivy`

Install Trivy vulnerability scanner binary.

---

## 📦 Caching & Utilities

### `setup-cache`

Configure system package caching (APT / package mirrors).

---

### `git-clone`

Clone repositories supporting shallow clones, full history, and authentication tokens.

```yaml
- uses: actions/forgejo/git-clone@v1
  with:
    repo: https://forgejo.example.com/user/repo.git
    token: ${{ secrets.TOKEN }}
    directory: repo
```

---

### `utils/detect-pkg-cache`

Automatically detect `pkg-cache` host domain from runner environment.

```yaml
- uses: actions/forgejo/utils/detect-pkg-cache@v1
  id: pkg
```

---

### Additional Utilities (`utils/`)
* **`get-latest-release`**: Fetch latest GitHub/Forgejo release assets.
* **`get-latest-tag`**: Fetch latest Git tag.
* **`inject-credentials`**: Inject credentials into configuration files.
* **`set-image`**: Format image reference names and namespaces.

---

# 🤖 AI Agent Integration & Skills

This repository includes vendor-neutral **AI Agent Operating Guidelines** (`AGENTS.md`) and **Agent Skills** compatible with GitHub Copilot CLI, Claude Code, Cursor, OpenHands, Aider, Windsurf, AutoGen, and other AI assistants.

Available skills in `.agents/skills/` and `skills/`:
* `action-creator`: Scaffold and create new composite actions adhering to repository standards.
* `action-validator`: Lint YAML syntax, verify `shell: bash` parameters, and validate shell safety.
* `docker-ci`: Automate Docker builds, multi-platform targets, and Trivy scans.
* `runtime-setup`: Manage runtime installer actions and `pkg-cache` configurations.
* `release-manager`: Automate `v1` major version tag updates.

---

# 🧩 Directory Structure

```
actions/
 ├ build-angular
 ├ build-hugo
 ├ clean-sync
 ├ container-scan
 ├ deploy-pages
 ├ docker-build
 ├ docker-login
 ├ docker-multi-build
 ├ docker-push
 ├ git-clone
 ├ link-docker-image
 ├ publish-maven
 ├ security-scan
 ├ setup-cache
 ├ setup-docker
 ├ setup-go
 ├ setup-gradle
 ├ setup-hugo
 ├ setup-java
 ├ setup-maven
 ├ setup-node
 ├ setup-trivy
 └ utils
      ├ detect-pkg-cache
      ├ get-latest-release
      ├ get-latest-tag
      ├ inject-credentials
      └ set-image
```

---

# 🚀 Example Pipeline Workflow

```yaml
name: CI Pipeline Example

on:
  push:
    branches: [main]

jobs:
  build-and-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Detect Package Cache
        uses: actions/forgejo/utils/detect-pkg-cache@v1
        id: pkg

      - name: Setup Node
        uses: actions/forgejo/setup-node@v1
        with:
          node_version: 20
          pkg_cache: ${{ steps.pkg.outputs.pkg_cache }}

      - name: Run Security Scan
        uses: actions/forgejo/security-scan@v1
        with:
          severity: "HIGH,CRITICAL"

      - name: Build Angular App
        uses: actions/forgejo/build-angular@v1
        with:
          working_dir: app
          base_href: "/"
```

---

# 🎯 Goals

This action collection aims to:

* Simplify CI/CD pipelines across **Forgejo, Gitea, and GitHub Actions**.
* Accelerate builds using **pkg-cache mirrors** and self-hosted optimizations.
* Provide **secure, vendor-neutral CI primitives** with built-in scanning.

---

# 📜 License

MIT License

---

# 🏷️ Release & Tag Management

To recreate or push major version tags (e.g. `v1`):

```bash
# Force update v1 tag locally and remotely
git tag -d v1 || true
git push origin :refs/tags/v1 || true
git tag v1
git push origin v1
```