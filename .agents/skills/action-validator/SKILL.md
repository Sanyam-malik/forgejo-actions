---
name: action-validator
description: Lint, validate YAML syntax, check shell safety, and verify metadata across action files.
vendor_neutral: true
version: 1.0.0
triggers:
  - "validate actions"
  - "lint action.yml"
  - "check action syntax"
inputs:
  target_path:
    type: string
    description: "Path to action.yml or directory containing actions"
    default: "."
---

# Action Validator Skill

This vendor-neutral skill enables AI agents to systematically inspect, lint, and validate composite action definitions in this repository.

## Validation Checklist

1. **YAML Validity**:
   - Ensure target `action.yml` is valid YAML.
   - Verify top-level keys: `name`, `description`, `runs`.
   - Ensure `runs.using` is set to `composite`.

2. **Step Conventions**:
   - Verify every step under `runs.steps` has a `name` or `id`.
   - Ensure steps running bash commands specify `shell: bash`.
   - Check that inline bash scripts begin with strict error flags (`set -e` or `set -euo pipefail`).

3. **Input & Variable Safety**:
   - Verify all inputs defined under `inputs:` have a `description`.
   - Check that inputs referenced in bash code are passed via `env:` bindings rather than direct string expansion `${{ inputs.x }}` inside shell logic.
   - Ensure deprecated syntax like `::set-output` or `::add-path` is NOT used; confirm use of `$GITHUB_OUTPUT`, `$GITHUB_ENV`, and `$GITHUB_PATH`.

4. **ShellScript Validation**:
   - Run `shellcheck` (if installed) on external `.sh` scripts under `<action>/scripts/`.

## Agent Execution Steps

1. Find all `action.yml` files matching `target_path`.
2. Inspect each `action.yml` against the Validation Checklist above.
3. Report any violations with exact line numbers and proposed fixes.
