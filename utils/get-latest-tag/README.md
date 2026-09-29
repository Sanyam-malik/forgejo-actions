# Get Latest Tag

Fetch the latest Git tag from a repository URL

## Usage

```yaml
steps:
  - name: Get Latest Tag
    id: get-latest-tag
    uses: your-org/forgejo-actions/utils/get-latest-tag@v1
    with:
      repo_url: https://forgejo.example.com/owner/repository.git
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo_url` | Repository URL | Yes | — |
| `token` | Auth token for private repositories | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `tag` | Latest git tag |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
