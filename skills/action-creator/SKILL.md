---
name: action-creator
description: Scaffold and create a new composite CI action following repository standards.
vendor_neutral: true
version: 1.0.0
triggers:
  - "create a new action"
  - "add a new action"
  - "scaffold composite action"
inputs:
  action_name:
    type: string
    description: "The name of the action directory (e.g., 'setup-pnpm' or 'utils/check-disk')"
    required: true
  action_title:
    type: string
    description: "Human readable title for action.yml"
    required: true
  description:
    type: string
    description: "Short description of the action"
    required: true
  inputs_schema:
    type: array
    description: "List of input fields with name, description, default, required"
    required: false
---

# Action Creator Skill

This vendor-neutral agent skill guides AI agents in creating consistent, reliable composite CI actions for Forgejo, Gitea, and GitHub Actions environments.

## Execution Protocol

1. **Directory Placement**:
   - Primary domain actions: Create top-level directory `<action_name>/`.
   - Utility/helper actions: Create under `utils/<action_name>/`.

2. **File Structure Requirements**:
   - Target file: `<action_name>/action.yml`.
   - If auxiliary bash scripts are needed, place them in `<action_name>/scripts/<script_name>.sh` and grant executable permissions (`chmod +x`).

3. **Composite Action Specification**:
   - `runs.using` must always be `composite`.
   - Inline bash steps must specify `shell: bash`.
   - Script blocks must start with `set -e` or `set -euo pipefail`.
   - Pass GitHub action inputs into bash steps via `env:` keys to avoid injection or shell parsing bugs.

4. **Output Handling**:
   - Write step outputs using `$GITHUB_OUTPUT`: `echo "key=value" >> "$GITHUB_OUTPUT"`.
   - Write environment modifications using `$GITHUB_ENV` or `$GITHUB_PATH`.

5. **Documentation Protocol**:
   - Add the action details and example usage block to `Readme.md` under the appropriate category.
   - Update `AGENTS.md` directory tree if a new directory structure pattern is introduced.

## Template

```yaml
name: Action Title
description: Clear, concise summary of purpose.

inputs:
  input_name:
    description: Parameter explanation
    required: false
    default: "default_value"

outputs:
  output_name:
    description: Description of output
    value: ${{ steps.main.outputs.output_name }}

runs:
  using: composite
  steps:
    - id: main
      name: Execute step
      shell: bash
      env:
        INPUT_VAL: ${{ inputs.input_name }}
      run: |
        set -euo pipefail
        echo "output_name=${INPUT_VAL}" >> "$GITHUB_OUTPUT"
```
