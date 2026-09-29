# Security Scan

Run secrets and dependency vulnerability scans using Gitleaks and Trivy

## Usage

```yaml
steps:
  - name: Security Scan
    id: security-scan
    uses: your-org/forgejo-actions/security-scan@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `trivy_version` | Trivy version to install. Defaults to the latest release. | No | `latest` |
| `trivy_install_dir` | Directory to install the Trivy binary into. | No | `/usr/local/bin` |
| `pkg_cache` | Package cache host or base URL to mirror GitHub releases through. | No | `""` |
| `gitleaks_version` | Gitleaks version to install. Defaults to the latest release. | No | `latest` |
| `gitleaks_install_dir` | Directory to install the Gitleaks binary into. | No | `/usr/local/bin` |
| `scan_path` | Path to scan. | No | `.` |
| `severity` | Trivy severities to report. | No | `HIGH,CRITICAL` |
| `ignore_unfixed` | Ignore vulnerabilities that do not have a fixed version. | No | `true` |
| `fail_on_secrets` | Fail the action when Gitleaks detects secrets. | No | `true` |
| `fail_on_vulnerabilities` | Fail the action when Trivy detects vulnerabilities. | No | `true` |
| `post_pr_comment` | Post (or update) a pull request comment summarizing the scan results. | No | `true` |

## Outputs

| Name | Description |
| --- | --- |
| `trivy_version` | The Trivy version that was installed. |
| `gitleaks_version` | The Gitleaks version that was installed. |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- Pull-request operations require the relevant event context and a token with sufficient repository permissions.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
