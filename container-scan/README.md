# Trivy Container Scan

Scan a container image with Trivy, produce JSON and table reports, fail on defined severity rules, and post/update a PR comment with the results. This wraps run-vulnerability-scan (scan_type: image) plus post-comment.

## Usage

```yaml
steps:
  - name: Trivy Container Scan
    id: container-scan
    uses: your-org/forgejo-actions/container-scan@v1
    with:
      image: example-app
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `image` | Image reference to scan (e.g. registry.example.com/org/app:tag) | Yes | — |
| `severity` | Comma-separated severities to include in the scan/report (UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL) | No | `CRITICAL,HIGH,MEDIUM` |
| `fail_on` | Comma-separated subset of "severity" that causes the action to fail if found. Must be a subset of "severity" to have any effect. Leave empty to report only and never fail the build. | No | `CRITICAL,HIGH,MEDIUM` |
| `vuln_type` | Comma-separated vulnerability types to scan (os, library) | No | `os,library` |
| `ignore_unfixed` | Ignore vulnerabilities with no available fix | No | `false` |
| `output_dir` | Directory to write the JSON and table reports into | No | `trivy-results` |
| `trivy_version` | Trivy version to install if trivy is not already on PATH | No | `latest` |
| `pkg_cache` | Package cache host or base URL to install Trivy through, if an install is needed | No | `""` |
| `fail_build` | Fail this action when matching vulnerabilities are found or the scan errors out. | No | `true` |
| `post_pr_comment` | Post (or update) a pull request comment summarizing the scan results. | No | `true` |

## Outputs

| Name | Description |
| --- | --- |
| `json_report` | Path to the JSON report |
| `table_report` | Path to the table report |
| `vulnerability_count` | Number of vulnerabilities matching fail_on severities |
| `pr_comment_action` | One of "created", "updated", or "skipped". |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- Pull-request operations require the relevant event context and a token with sufficient repository permissions.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
