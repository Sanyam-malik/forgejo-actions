# Install Gitleaks

Install the Gitleaks CLI on the runner

## Usage

```yaml
steps:
  - name: Install Gitleaks
    id: setup-gitleaks
    uses: your-org/forgejo-actions/setup-gitleaks@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `version` | Gitleaks version to install (e.g. "8.18.0"). Defaults to the latest release. | No | `latest` |
| `install_dir` | Directory to install the gitleaks binary into. Must be on PATH, or added to PATH by this action. | No | `/usr/local/bin` |
| `pkg_cache` | Package cache host or base URL to mirror GitHub releases through (e.g. an internal proxy). Falls back to github.com when empty. | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `version` | The Gitleaks version that was installed |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
