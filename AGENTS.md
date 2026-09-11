# AGENTS.md - Agent Operating Guidelines for Forgejo CI Actions

Welcome AI Agent! This document defines the repository architecture, coding guidelines, standards, and vendor-neutral agent skills for working with the **Forgejo CI Actions** codebase.

---

## 1. Repository Overview

This repository contains reusable **composite actions** designed for **Forgejo, Gitea, and GitHub Actions** compatible CI runners.

### Directory Structure
```
forgejo-actions/
├── build-angular/            # Angular build composite action
├── build-hugo/               # Hugo site build action
├── repository-sync/          # Branch/dir sync utility action
├── container-scan/           # Container image scanning action
├── deploy-pages/             # Git pages deployment action
├── docker-build/             # Docker single-platform build & OCI export
├── docker-login/             # Registry login action
├── docker-multi-build/       # Multi-platform build & platform validation action
├── docker-push/              # Docker image push action
├── docker-sync/              # Registry-to-registry image sync action
├── git-clone/                # Git clone utility action
├── link-docker-image/        # Package registry image linker
├── publish-maven/            # Maven/Gradle package publisher
├── security-scan/            # Secrets & dependency scanner (Gitleaks + Trivy)
├── setup-cache/              # System APT / package cache installer
├── setup-docker/             # Docker engine & Buildx installer
├── setup-go/                 # Go runtime installer
├── setup-gradle/             # Gradle installer with mirror support
├── setup-hugo/               # Hugo Extended installer
├── setup-java/               # OpenJDK installer
├── setup-node/               # Node.js installer with pkg-cache mirror
├── setup-trivy/              # Trivy security tool installer
├── utils/                    # Common helper composite actions
│   ├── detect-pkg-cache/     # Auto-detect pkg-cache hostname
│   ├── get-latest-release/   # Fetch GitHub/Forgejo release tarball
│   ├── get-latest-tag/       # Fetch latest git tag
│   ├── inject-credentials/   # Inject configuration credentials
│   └── set-image/            # Format image names and namespaces
├── .github/workflows/        # CI automation workflows
└── .agents/skills/           # Vendor-neutral agent skills
```

---

## 2. General Principles & Agent Conduct

1. **Vendor Neutrality**: Do not rely on vendor-specific syntax or proprietary extensions. Keep actions compatible across Forgejo, Gitea, and GitHub Actions environments.
2. **Composite Action Standard**: All actions in this repo use `runs.using: composite`. Do not use JavaScript/Node runner actions (`using: node20`) unless explicitly required.
3. **Robust Shell Scripting**:
   - Always set strict error flags in inline scripts: `set -e` or `set -euo pipefail`.
   - Pass inputs to bash scripts using environment variables (`env:`) rather than inline string interpolation (`${{ inputs.foo }}`) inside raw bash commands when variables may contain spaces or special characters.
   - Use `$GITHUB_OUTPUT` and `$GITHUB_ENV` file commands rather than deprecated `::set-output`.
4. **Mirror & Offline First Support**:
   - Support `pkg_cache` mirror parameters where applicable to allow air-gapped or accelerated CI environments.
   - Always fallback gracefully to official distribution endpoints if `pkg_cache` is empty.

---

## 3. Standard Action Template

When creating a new action directory `<action-name>/action.yml`, adhere to this specification:

```yaml
name: Action Title
description: Clear, concise description of what the action does.

inputs:
  param_name:
    description: Parameter description
    required: false
    default: "default-value"

outputs:
  output_name:
    description: Output description
    value: ${{ steps.step_id.outputs.output_name }}

runs:
  using: composite
  steps:
    - id: step_id
      name: Step Name
      shell: bash
      env:
        PARAM_NAME: ${{ inputs.param_name }}
      run: |
        set -euo pipefail

        # Action implementation logic
        echo "output_name=computed-value" >> "$GITHUB_OUTPUT"
```

---

## 4. Vendor-Neutral Agent Skills

This repository provides vendor-neutral agent skills stored under `.agents/skills/` and `skills/`. Any AI coding assistant (Copilot CLI, Claude Code, Cursor, OpenHands, Aider, Windsurf, AutoGen, etc.) can discover and execute these skills:

| Skill ID | Description | Location |
| :--- | :--- | :--- |
| `action-creator` | Scaffold and create a new composite CI action | `.agents/skills/action-creator/SKILL.md` |
| `action-validator` | Lint, validate syntax, and check bash safety of `action.yml` files | `.agents/skills/action-validator/SKILL.md` |
| `docker-ci` | Configure, build, export, and push Docker OCI images | `.agents/skills/docker-ci/SKILL.md` |
| `runtime-setup` | Implement language runtime setup actions with `pkg-cache` support | `.agents/skills/runtime-setup/SKILL.md` |
| `release-manager` | Manage release tags (`v1`) and workflow dispatch events | `.agents/skills/release-manager/SKILL.md` |

---

## 5. Development & Testing Instructions

### Validating Actions
- Verify YAML format and syntax for all `action.yml` files.
- Run `shellcheck` (if available) on shell scripts inside action steps or external scripts.
- Ensure all inputs have description fields and reasonable default values where possible.

### Release Tagging
- Major version tags (e.g. `v1`) are updated via `.github/workflows/recreate-tag.yml`.
- Manual tag reset commands:
  ```bash
  git tag -d v1 || true
  git push origin :refs/tags/v1 || true
  git tag v1
  git push origin v1
  ```

---

## 6. Definition of Done for Agents

Before completing any task:
1. Ensure all modified `action.yml` files follow strict composite action conventions.
2. Verify shell script error handling (`set -euo pipefail` or `set -e`).
3. Update `Readme.md` if adding a new action or adding/modifying input parameters.
4. Ensure no hardcoded credentials or environment-specific hostnames exist outside `pkg_cache` inputs.
