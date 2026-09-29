---
name: action-documentation
description: Create and maintain action-level README documentation for composite actions.
vendor_neutral: true
version: 1.0.0
triggers:
  - "document an action"
  - "create an action README"
  - "update action documentation"
inputs:
  action_name:
    type: string
    description: Action directory to document.
    required: true
---

# Action Documentation Skill

Use this skill when a composite action needs an action-local `README.md`.

Read the action's `action.yml`, scripts, templates, and repository-level
documentation first. Create `<action>/README.md` with its purpose, workflow
context, usage example, input table, output table, and architecture or
file-format details when applicable.

Keep documented inputs, defaults, required flags, outputs, and behavior
synchronized with `action.yml`. Document delegated actions and generated
files explicitly, update the repository README and skill indexes when public
behavior changes, keep examples vendor-neutral, and avoid hard-coded
credentials.

Verify every documented input and output exists in `action.yml`, remove claims
that refactoring made obsolete, and run YAML validation after metadata changes.
