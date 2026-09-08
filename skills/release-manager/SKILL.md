---
name: release-manager
description: Manage version tagging (v1) and release workflow automation for Forgejo Actions.
vendor_neutral: true
version: 1.0.0
triggers:
  - "recreate tag"
  - "release v1"
  - "update tag"
  - "publish version"
---

# Release Manager Skill

This skill enables AI agents to automate git tag management and release workflows for actions in this repository.

## Release Model

Action users consume actions using the major release tag (e.g., `uses: actions/forgejo/setup-node@v1`).
Whenever changes are merged into `main`, the `v1` tag must be force-updated to point to the latest commit on `main`.

## Tag Recreation Procedure

1. **Automated via GitHub / Forgejo Workflow**:
   - Workflow file: `.github/workflows/recreate-tag.yml`.
   - Triggers: `push` on `main` branch or `workflow_dispatch`.

2. **Manual Git Execution**:
   ```bash
   # Ensure local main branch is fully up to date
   git checkout main
   git pull origin main

   # Delete existing local & remote v1 tag
   git tag -d v1 || true
   git push origin :refs/tags/v1 || true

   # Create and push fresh v1 tag
   git tag v1
   git push origin v1
   ```

3. **Validation**:
   - Verify `git tag -l` lists `v1`.
   - Verify `git rev-parse v1` matches `git rev-parse HEAD`.
