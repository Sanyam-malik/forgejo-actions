# Detect Package Cache

Compatibility utility that derives a package-cache hostname from a server URL.
For new workflows, prefer [`setup-cache`](../../setup-cache/), which performs
this detection automatically, configures system repositories, and exports the
normalized result as `PKG_CACHE` for all subsequent actions.

## Usage

```yaml
steps:
  - id: detect-pkg-cache
    uses: your-org/forgejo-actions/utils/detect-pkg-cache@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `server_url` | Server URL used to derive the cache domain | No | `${{ github.server_url }}` |

## Outputs

| Name | Description |
| --- | --- |
| `pkg_cache` | Derived package-cache hostname, without a URL scheme |

This utility does not modify repositories or export `PKG_CACHE`; use
`setup-cache` when configuring a workflow.
