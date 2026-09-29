# Get Latest Release Assets

Fetch latest release assets from GitHub / Gitea / Forgejo compatible APIs

## Usage

```yaml
steps:
  - name: Get Latest Release Assets
    id: get-latest-release
    uses: your-org/forgejo-actions/utils/get-latest-release@v1
    with:
      repo: owner/repository
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo` | Repository URL | Yes | — |
| `api_url` | API base URL (e.g. https://api.github.com or https://gitea.example.com/api/v1) | No | `https://api.github.com` |
| `token` | API token | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Latest release tag |
| `assets` | JSON array of assets |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- API operations require a compatible server endpoint and a token with sufficient permissions when authentication is needed.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
