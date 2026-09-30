# Get Release

Fetches a selected release and its assets from GitHub, GitLab, Gitea, Forgejo,
or OneDev. The default `version: latest` delegates to the provider-aware
`utils/get-latest-release` implementation. A selected version uses the
provider's release API and falls back to verifying the corresponding git tag
when a release API is unavailable.

## Usage

```yaml
steps:
  - id: release
    uses: your-org/forgejo-actions/utils/get-release@v1
    with:
      repo: https://gitlab.com/group/subgroup/project.git
      version: v2.4.0
      token: ${{ secrets.REPOSITORY_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo` | Repository URL (HTTPS or SSH) | Yes | — |
| `version` | Exact release/tag to fetch, or `latest` | No | `latest` |
| `api_url` | Optional API base URL override | No | `""` |
| `provider` | Provider override: `github`, `gitlab`, `gitea`, `forgejo`, or `onedev` | No | `""` |
| `token` | Optional API/git token | No | `""` |

When `PKG_CACHE` is set, GitHub API requests and GitHub asset URLs use that
mirror. GitLab paths are URL-encoded. OneDev tag-only fallbacks return
`assets: []`.

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Selected release tag |
| `assets` | Compact JSON array of `{name,size,url}` objects |
