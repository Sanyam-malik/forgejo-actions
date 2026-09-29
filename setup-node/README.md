# Setup Node

Install Node.js with optional pkg-cache mirror

## Usage

```yaml
steps:
  - name: Setup Node
    id: setup-node
    uses: your-org/forgejo-actions/setup-node@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `node_version` | Node.js major version (e.g. 20, 21) | No | `20` |
| `pkg_cache` | pkg-cache host or base URL | No | `""` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
