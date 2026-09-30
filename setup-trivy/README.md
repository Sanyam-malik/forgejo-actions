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

## Outputs

| Name | Description |
| --- | --- |
| `version` | The Trivy version that was installed |

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
