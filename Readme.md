# Forgejo CI Actions

A production-ready collection of **reusable composite actions** designed for **Forgejo, Gitea, and GitHub Actions compatible CI/CD pipelines**.

These actions simplify common CI tasks such as:

* ⚙️ Language runtime setup with mirror support
* 🐳 Docker build, multi-platform build, OCI export, and push
* 🛡️ Security & vulnerability scanning (Gitleaks + Trivy)
* 🔎 Pull-request code review with linters or OpenAI-compatible AI models
* 🌐 Static site building & deployment
* 📦 Package publishing (Maven & Gradle)
* 🧰 Git operations & package cache integrations

The actions are optimized for **self-hosted runners**, **air-gapped networks**, and **multi-platform CI environments**.

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

### `repository-sync`

Reinitialize repository history and push clean commits to a target remote.

```yaml
- uses: actions/forgejo/repository-sync@v1
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

### `docker-sync`

Sync/copy Docker container images from the current Forgejo repository package registry to external registries (e.g. GCR, Docker Hub, GHCR).

Auto-discovers linked container packages from the current repository via Forgejo API:

```yaml
- uses: actions/forgejo/docker-sync@v1
  with:
    target_registry: gcr.io
    target_namespace: my-gcp-project
    target_tag: canary,latest
    target_username: _json_key
    target_token: ${{ secrets.GCP_SA_KEY }}
```

---

### `link-docker-image`

Link container images with repository package registries.

---

## ⚙️ Language Setup & Publishing Actions

### `setup-node`

Install Node.js.

```yaml
- uses: actions/forgejo/setup-node@v1
  with:
    node_version: 20
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

Install a Java distribution.

```yaml
- uses: actions/forgejo/setup-java@v1
  with:
    java_version: "21"
    distribution: "temurin"
```

---

### `setup-maven`

Install Apache Maven with automatic version resolution.

```yaml
- uses: actions/forgejo/setup-maven@v1
  with:
    maven_version: "latest"
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

## 🔎 Code Review Actions

### `code-review`

Run MegaLinter and reviewdog against changed pull-request files. This action
produces review items as JSON, then delegates shared severity filtering,
fingerprint de-duplication, existing-comment handling, auto-resolution,
comment posting, and fail-level enforcement to `code-analyzer`.

```yaml
- uses: actions/forgejo/code-review@v1
  with:
    level: error
    filter-mode: changed_files
    skip-existing: true
    fail-level: warning
    token: ${{ github.token }}
```

### `ai-code-review`

Review changed pull-request files with an OpenAI-compatible endpoint such as
Ollama, llama.cpp, vLLM, or OpenAI. The action writes an AI review envelope
containing findings and review metadata; `code-analyzer` handles the shared
lifecycle and posts inline comments.

```yaml
- uses: actions/forgejo/ai-code-review@v1
  with:
    ai-base-url: https://api.openai.com/v1
    ai-model: gpt-4o
    ai-api-key: ${{ secrets.OPENAI_API_KEY }}
    level: warning
    skip-existing: true
    max-comments: 0
    fail-level: none
    token: ${{ github.token }}
```

Both producer actions must run in a pull-request workflow and require a token
with permission to read pull-request files and review comments. Use
`code-analyzer` directly when another review tool already produces a JSON
array or an object containing an `items` array.

## 🛡️ Security & Scanning Actions

### `code-analyzer`

Apply shared filtering and fingerprint deduplication to review findings,
auto-mark stale comments as fixed, post inline pull-request comments through
`post-file-comment`, and enforce the configured fail level. It accepts a JSON
array or producer envelope and is used by `code-review` and `ai-code-review`.

The producer JSON items must include `path`, `line`, `message`, and
`severity`. Optional fields such as `tool`, `rule_code`, `title`, `category`,
`confidence`, and pre-rendered template fields are preserved for
`message-template-file`. An envelope may also include `summary` metadata.

```yaml
- uses: actions/forgejo/code-analyzer@v1
  with:
    items-file: review-items.json
    message-template-file: templates/review-comment.md
    level: warning
    fingerprint-mode: lint
    fingerprint-prefix: lint-review
    fail-level: warning
    token: ${{ github.token }}
```

### `security-scan`

Run comprehensive secret detection (Gitleaks) and dependency vulnerability scans (Trivy).

```yaml
- uses: actions/forgejo/security-scan@v1
  with:
    severity: "HIGH,CRITICAL"
    fail_on_secrets: true
    fail_on_vulnerabilities: true
```

When the scanned branch has an open pull request, the action posts the security
scan summary as a pull request comment. The workflow token must have permission
to write pull request or issue comments.

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

Configure system package repositories for subsequent actions.

```yaml
steps:
  - uses: actions/forgejo/setup-cache@v1
  - uses: actions/forgejo/setup-node@v1
    with:
      node_version: 20
```

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

### `condition-check`

Check whether a value matches a regular expression.

**Features:**
* Evaluates input string against a regular expression pattern using Bash regex.
* Outputs `matches` (`true` or `false`).

```yaml
- uses: actions/forgejo/condition-check@v1
  id: check
  with:
    value: "v1.2.3"
    regex: "^v[0-9]+\\.[0-9]+\\.[0-9]+$"
```

---

### `utils/detect-pkg-cache`

Compatibility utility for detecting a package-cache host domain. New workflows
should use `setup-cache`.

```yaml
- uses: actions/forgejo/utils/detect-pkg-cache@v1
  id: pkg
```

---

### Additional Utilities (`utils/`)
* **`get-latest-release`**: Fetch latest release assets from GitHub, GitLab, Gitea, Forgejo, or OneDev.
* **`get-latest-tag`**: Fetch the latest tag from any supported provider using git.
* **`get-release`**: Fetch a selected release (or the latest release by default).
* **`get-tag`**: Fetch a selected tag (or the latest tag by default).
* **`inject-credentials`**: Inject credentials into configuration files.
* **`set-image`**: Format image reference names and namespaces.

The tag and release utilities derive provider and repository identity from the
repository URL. Use `provider` or `api_url` only when an installation needs an
explicit override.

---

# 🤖 AI Agent Integration & Skills

This repository includes vendor-neutral **AI Agent Operating Guidelines** (`AGENTS.md`) and **Agent Skills** compatible with GitHub Copilot CLI, Claude Code, Cursor, OpenHands, Aider, Windsurf, AutoGen, and other AI assistants.

Available skills in `.agents/skills/` and `skills/`:
* `action-creator`: Scaffold and create new composite actions adhering to repository standards.
* `action-validator`: Lint YAML syntax, verify `shell: bash` parameters, and validate shell safety.
* `action-documentation`: Create and maintain action-level README files synchronized with `action.yml`.
* `pkg-cache-enforcement`: Ensure every network download uses the configured package cache when supported.
* `docker-ci`: Automate Docker builds, multi-platform targets, and Trivy scans.
* `runtime-setup`: Manage runtime installer actions and package-cache integrations.
* `release-manager`: Automate `v1` major version tag updates.

---

# 🧩 Directory Structure

```
actions/
 ├ build-angular
 ├ build-hugo
 ├ ai-code-review
 ├ code-analyzer
 ├ code-review
 ├ condition-check
 ├ container-scan
 ├ deploy-pages
 ├ docker-build
 ├ docker-login
 ├ docker-multi-build
 ├ docker-push
 ├ docker-sync
 ├ git-clone
 ├ inactive-lock
 ├ link-docker-image
 ├ post-comment
 ├ post-file-comment
 ├ publish-maven
 ├ repository-sync
 ├ run-secrets-scan
 ├ run-vulnerability-scan
 ├ security-scan
 ├ setup-cache
 ├ setup-docker
 ├ setup-gitleaks
 ├ setup-go
 ├ setup-gradle
 ├ setup-hugo
 ├ setup-java
 ├ setup-maven
 ├ setup-node
 ├ setup-python
 ├ setup-trivy
 └ utils
      ├ detect-pkg-cache
      ├ get-latest-release
      ├ get-latest-tag
      ├ get-release
      ├ get-tag
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

      - name: Setup Package Cache
        uses: actions/forgejo/setup-cache@v1

      - name: Setup Node
        uses: actions/forgejo/setup-node@v1
        with:
          node_version: 20

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
* Accelerate builds using self-hosted optimizations.
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