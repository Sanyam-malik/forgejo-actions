# Repository Sync

Reinitialize repo and push clean history to any git remote

## Usage

```yaml
steps:
  - name: Repository Sync
    id: repository-sync
    uses: your-org/forgejo-actions/repository-sync@v1
    with:
      remote_url: https://forgejo.example.com/owner/repository.git
      user_name: CI Bot
      user_email: ci@example.com
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `remote_url` | Base git remote URL (without credentials) | Yes | — |
| `token` | Auth token (used for HTTPS remotes) | No | — |
| `user_name` | Git username | Yes | — |
| `user_email` | Git email | Yes | — |
| `branch` | Branch to push | No | `main` |
| `commit_message` | Commit message | No | `""` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
