# Forgejo CI Actions

A collection of **reusable composite actions** designed for **Forgejo / Gitea / GitHub compatible CI pipelines**.

These actions simplify common CI tasks such as:

* Language runtime setup
* Docker build & push
* Static site deployment
* Maven publishing
* Git utilities
* Package cache integration

The actions are designed to work with **self-hosted runners**, **pkg-cache mirrors**, and **multi-platform CI environments**.

---

# 📦 Available Actions

## Build Actions

### `build-angular`

Build an Angular project.

Features:

* Installs dependencies
* Optional `--force` install
* Configurable base href
* Configurable build configuration
* Supports custom working directory

Example:

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

Example:

```yaml
- uses: actions/forgejo/build-hugo@v1
  with:
    working_dir: site
    base_url: "/blog/"
```

---

## Deployment Actions

### `deploy-pages`

Deploy static site content to a `gh-pages` branch.

Features:

* Cleans orphan branch
* Removes nested git repositories
* Supports arbitrary build output directory

Example:

```yaml
- uses: actions/forgejo/deploy-pages@v1
  with:
    site_path: dist
    git_user: CI Bot
    git_email: ci@example.com
```

---

## Docker Actions

### `docker-login`

Login to container registry.

### `docker-build`

Build Docker image.

### `docker-push`

Push Docker image to registry.

### `link-docker-image`

Link image with repository package registry.

Example:

```yaml
- uses: actions/forgejo/docker-login@v1
- uses: actions/forgejo/docker-build@v1
- uses: actions/forgejo/docker-push@v1
```

---

## Language Setup Actions

### `setup-node`

Install Node.js with optional **pkg-cache mirror**.

Features:

* Auto-detect latest patch version
* Supports Node major versions
* Optional npm registry mirror

Example:

```yaml
- uses: actions/forgejo/setup-node@v1
  with:
    node_version: 20
    pkg_cache: ${{ steps.pkg.outputs.pkg_cache }}
```

---

### `setup-go`

Install Go runtime.

### `setup-java`

Install OpenJDK.

### `setup-gradle`

Install Gradle with optional cache mirror.

### `setup-hugo`

Install Hugo Extended.

---

## Cache Setup

### `setup-cache`

Configure system package caching (APT / mirrors).

---

## Git Utilities

### `git-clone`

Clone a repository with support for:

* shallow clone
* full clone
* authentication token

Example:

```yaml
- uses: actions/forgejo/git-clone@v1
  with:
    repo: https://forgejo.example.com/user/repo.git
    token: ${{ secrets.TOKEN }}
    directory: repo
```

---

## Utility Actions

Located under `utils/`.

### `detect-pkg-cache`

Detect pkg-cache mirror automatically.

### `get-latest-release`

Fetch latest release assets.

### `get-latest-tag`

Fetch latest Git tag.

### `inject-credentials`

Inject credentials into configuration files.

### `set-image`

Generate Docker image name and namespace.

---

# 🧩 Directory Structure

```
actions/
 ├ build-angular
 ├ build-hugo
 ├ deploy-pages
 ├ docker-build
 ├ docker-login
 ├ docker-push
 ├ git-clone
 ├ link-docker-image
 ├ publish-maven
 ├ setup-cache
 ├ setup-go
 ├ setup-gradle
 ├ setup-hugo
 ├ setup-java
 ├ setup-node
 └ utils
      ├ detect-pkg-cache
      ├ get-latest-release
      ├ get-latest-tag
      ├ inject-credentials
      └ set-image
```

---

# 🚀 Example Workflow

```yaml
name: Build Angular

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ownubuntu

    steps:
      - uses: actions/checkout@v4

      - uses: actions/forgejo/utils/detect-pkg-cache@v1
        id: pkg

      - uses: actions/forgejo/setup-node@v1
        with:
          node_version: 20
          pkg_cache: ${{ steps.pkg.outputs.pkg_cache }}

      - uses: actions/forgejo/build-angular@v1
        with:
          working_dir: app
          base_href: "/"
          force_install: true
```

---

# 🎯 Goals

This action collection aims to:

* simplify CI pipelines
* support **Forgejo / Gitea ecosystems**
* integrate with **pkg-cache mirrors**
* provide **reusable CI primitives**

---

# 📜 License

MIT License

# Commands

## Removing tag

```
git tag -l | xargs -n 1 git push --delete origin
git tag -l | xargs git tag -d
```

## Creating tag

```
git tag v1                                      
git push origin v1
```