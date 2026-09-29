# Run Secrets Scan

Run a Gitleaks secrets scan and produce a JSON report

## Usage

```yaml
steps:
  - name: Run Secrets Scan
    id: run-secrets-scan
    uses: your-org/forgejo-actions/run-secrets-scan@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `scan_path` | Path to scan. | No | `.` |
| `report_path` | Path to write the Gitleaks JSON report to. Defaults to a file under the runner's temp directory. | No | `""` |
| `gitleaks_version` | Gitleaks version to install if gitleaks is not already on PATH. | No | `latest` |
| `gitleaks_install_dir` | Directory to install the Gitleaks binary into, if an install is needed. Must be on PATH, or added to PATH by the install. | No | `/usr/local/bin` |
| `pkg_cache` | Package cache host or base URL to install Gitleaks through, if an install is needed. | No | `""` |
| `fail_build` | If "true", this action fails itself (exit 1) when secret_count is greater than zero, or when the scan errors out. If "false" (default), the action only reports - the caller decides whether to fail the build based on the outputs. | No | `false` |

## Outputs

| Name | Description |
| --- | --- |
| `report` | Path to the Gitleaks JSON report |
| `secret_count` | Number of secrets detected |
| `scan_error` | "true" if Gitleaks failed to complete the scan (as opposed to completing the scan and finding secrets). Callers should treat this as a hard failure rather than trusting secret_count, since the report may be incomplete. |
| `gitleaks_version` | The Gitleaks version that was used for the scan |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
