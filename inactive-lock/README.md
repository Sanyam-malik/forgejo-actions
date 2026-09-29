# Forgejo Lock Inactive

Lock inactive Forgejo issues and pull requests after a configurable number of days

## Usage

```yaml
steps:
  - name: Forgejo Lock Inactive
    id: inactive-lock
    uses: your-org/forgejo-actions/inactive-lock@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `days` | Number of days without activity before locking | No | `30` |
| `token` | Forgejo API token | No | `${{ github.token }}` |
| `issues` | Process issues | No | `true` |
| `pull-requests` | Process pull requests | No | `true` |
| `exclude-labels` | Comma-separated labels that prevent an issue or pull request from being locked | No | `""` |
| `include-drafts` | Lock draft pull requests | No | `false` |
| `comment` | Comment posted immediately before locking | No | `This conversation has been inactive for ${{ inputs.days }} days and has been locked.` |
| `dry-run` | Report what would be locked without making changes | No | `false` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Pull-request operations require the relevant event context and a token with sufficient repository permissions.
