# Get Tag

Fetches a selected tag from a GitHub, GitLab, Gitea, Forgejo, or OneDev
repository. With the default `version: latest`, this uses the same git-based
resolution as `utils/get-latest-tag`.

## Usage

```yaml
steps:
  - id: tag
    uses: your-org/forgejo-actions/utils/get-tag@v1
    with:
      repo_url: https://github.com/example/project.git
      version: v2.4.0
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo_url` | Repository clone URL (HTTPS or SSH) | Yes | — |
| `version` | Exact tag to fetch, or `latest` | No | `latest` |
| `token` | Optional token for private repositories | No | `""` |
| `provider` | Provider override: `github`, `gitlab`, `gitea`, `forgejo`, or `onedev` | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Selected tag |
