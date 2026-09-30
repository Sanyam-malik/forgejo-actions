# Setup Node

Install Node.js with inherited PKG_CACHE mirror support

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

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
