# Get Latest Release

Fetches the latest release tag and assets from GitHub, GitLab, Gitea, Forgejo,
or OneDev. Provider and repository identity are derived from the repository
URL. OneDev and installations without a release REST API fall back to the
latest git tag and return an empty asset list.

## Usage

```yaml
steps:
  - id: latest-release
    uses: your-org/forgejo-actions/utils/get-latest-release@v1
    with:
      repo: https://gitlab.com/group/subgroup/project.git
      token: ${{ secrets.REPOSITORY_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo` | Repository URL (HTTPS or SSH) | Yes | — |
| `api_url` | Optional API base URL override | No | `""` |
| `provider` | Provider override: `github`, `gitlab`, `gitea`, `forgejo`, or `onedev` | No | `""` |
| `token` | Optional API/git token | No | `""` |

GitLab project paths are URL-encoded for API calls. When `PKG_CACHE` is
available, GitHub API requests and GitHub asset URLs use the mirror; other
provider URLs remain direct.

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Latest release tag, or latest git tag when no release API is available |
| `assets` | Compact JSON array of `{name,size,url}` objects |
