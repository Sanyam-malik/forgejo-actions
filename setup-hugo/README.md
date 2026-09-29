# Setup Hugo

Install Hugo Extended from official release

## Usage

```yaml
steps:
  - name: Setup Hugo
    id: setup-hugo
    uses: your-org/forgejo-actions/setup-hugo@v1
    with:
      hugo_version: 0.146.0
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `hugo_version` | Hugo version | Yes | — |
| `pkg_cache` | Package cache host or base URL | No | `""` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
