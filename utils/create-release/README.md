# Create Tag and Release

Creates or updates a git tag and creates or updates the corresponding release
using the GitHub-compatible REST API exposed by GitHub, Forgejo, or Gitea.

```yaml
- name: Create release
  id: release
  uses: your-org/forgejo-actions/utils/create-release@v1
  with:
    tag: v1.2.3
    name: v1.2.3
    body_file: RELEASE.md
    placeholders: '{"VERSION":"v1.2.3","DATE":"2026-10-02"}'
    token: ${{ secrets.RELEASE_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repository` | Repository in `owner/name` form or URL | No | `${{ github.repository }}` |
| `tag` | Tag name | Yes | — |
| `name` | Release name | No | Tag name |
| `body_file` | File containing release description | No | `RELEASE.md` |
| `placeholders` | JSON object replacing `{{KEY}}` markers | No | `{}` |
| `target_commitish` | Commit SHA or branch for the tag | No | `${{ github.sha }}` |
| `token` | Token with tag/release write permission | No | `${{ github.token }}` |
| `api_url` | API base URL override | No | `${{ github.api_url }}` |
| `force_tag` | Move an existing tag to the target commit | No | `false` |
| `draft` | Create a draft release | No | `false` |
| `prerelease` | Mark the release as prerelease | No | `false` |

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Created tag |
| `release_id` | Release identifier |
| `release_url` | Release web URL |

The action reads `RELEASE.md` by default, or the file specified by `body_file`.
The file must exist. Placeholders use the `{{KEY}}` syntax and are replaced
from the JSON object provided through `placeholders`.
