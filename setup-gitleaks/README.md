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

## Outputs

| Name | Description |
| --- | --- |
| `version` | The Gitleaks version that was installed |

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
