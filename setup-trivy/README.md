# Install Trivy

Install the Trivy CLI on the runner

## Usage

```yaml
steps:
  - name: Install Trivy
    id: setup-trivy
    uses: your-org/forgejo-actions/setup-trivy@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `version` | Trivy version to install (e.g. "0.55.2"). Defaults to the latest release. | No | `latest` |
| `install_dir` | Directory to install the trivy binary into. Must be on PATH, or added to PATH by this action. | No | `/usr/local/bin` |
| `pkg_cache` | Package cache host or base URL to mirror GitHub releases through (e.g. an internal proxy). Falls back to github.com when empty. | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `version` | The Trivy version that was installed |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
