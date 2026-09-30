# Get Latest Tag

Resolves the newest tag from a GitHub, GitLab, Gitea, Forgejo, or OneDev
repository using the git protocol. This works even when a provider does not
offer a compatible REST API.

## Usage

```yaml
steps:
  - id: latest-tag
    uses: your-org/forgejo-actions/utils/get-latest-tag@v1
    with:
      repo_url: https://forgejo.example.com/owner/repository.git
      token: ${{ secrets.REPOSITORY_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo_url` | Repository clone URL (HTTPS or SSH) | Yes | — |
| `token` | Optional token for private repositories | No | `""` |
| `provider` | Provider override: `github`, `gitlab`, `gitea`, `forgejo`, or `onedev` | No | `""` |
| `api_url` | Optional API base URL override for provider-compatible callers (not needed for git resolution) | No | `""` |

Provider identity is derived from the repository host. The token is passed
through the environment to git and is never embedded in the repository URL.

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Newest tag according to version-aware sorting |
