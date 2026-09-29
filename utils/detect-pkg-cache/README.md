# Detect Package Cache

Detect package cache hostname from server URL

## Usage

```yaml
steps:
  - name: Detect Package Cache
    id: detect-pkg-cache
    uses: your-org/forgejo-actions/utils/detect-pkg-cache@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `server_url` | Server URL used to derive cache domain | No | `${{ github.server_url }}` |

## Outputs

| Name | Description |
| --- | --- |
| `pkg_cache` | Package cache hostname |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.
