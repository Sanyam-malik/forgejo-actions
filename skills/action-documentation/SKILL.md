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

## Procedure

1. Read the action's `action.yml`, scripts, templates, and repository-level
   documentation before writing.
2. Create `<action>/README.md` with the action purpose, supported workflow
   context, usage example, input table, output table, and architecture or
   file-format details when applicable.
3. Keep input names, defaults, required flags, output names, and behavior
   synchronized with `action.yml`; treat `action.yml` as authoritative.
4. Document delegated actions and generated files explicitly when the action
   is a producer or wrapper.
5. Update the repository `Readme.md` and skill indexes when the action's public
   behavior changes.
6. Keep examples vendor-neutral and avoid hard-coded credentials.

## Quality checks

- Verify every documented input and output exists in `action.yml`.
- Remove claims that the action no longer performs after a refactor.
- Use fenced YAML/JSON examples that are copyable.
- Run YAML validation after changing action metadata.
